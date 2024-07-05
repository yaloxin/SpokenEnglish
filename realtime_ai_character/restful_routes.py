import asyncio
import datetime
import os
import uuid
from typing import Optional

import firebase_admin
import httpx
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    status as http_status,
    UploadFile,
)
from firebase_admin import auth, credentials
from firebase_admin.exceptions import FirebaseError
from google.cloud import storage
from sqlalchemy import func
from sqlalchemy.orm import Session

from realtime_ai_character.audio.text_to_speech import get_text_to_speech
from realtime_ai_character.database.connection import get_db
from realtime_ai_character.llm.highlight_action_generator import (
    generate_highlight_action,
    generate_highlight_based_on_prompt,
)
from realtime_ai_character.llm.system_prompt_generator import generate_system_prompt
from realtime_ai_character.models.interaction import Interaction
from realtime_ai_character.models.feedback import Feedback, FeedbackRequest
from realtime_ai_character.models.character import (
    Character,
    CharacterRequest,
    EditCharacterRequest,
    DeleteCharacterRequest,
    GenerateHighlightRequest,
    GeneratePromptRequest,
)

'''
定义了一个名为 router 的 APIRouter 对象，用于定义和处理 API 的各个端点。'''
router = APIRouter()
'''
根据环境变量 USE_AUTH 的值判断是否启用身份验证，如果启用了，则初始化 Firebase 应用程序。'''
if os.getenv("USE_AUTH") == "true":
    cred = credentials.Certificate(os.environ.get("FIREBASE_CONFIG_PATH"))
    firebase_admin.initialize_app(cred)
'''
定义了一个常量 MAX_FILE_UPLOADS，表示最大文件上传数量
'''
MAX_FILE_UPLOADS = 5

'''
定义了一个异步函数 get_current_user(request: Request)，用于从请求中获取当前用户信息。
如果请求已经进行了身份验证并且验证通过，则返回当前用户的信息，否则返回 None。'''
async def get_current_user(request: Request):
    """Returns the current user if the request is authenticated, otherwise None.

    """
    if os.getenv("USE_AUTH") == "true" and "Authorization" in request.headers:
        # Extracts the token from the Authorization header
        tokens = request.headers.get("Authorization", "").split("Bearer ")
        if not tokens or len(tokens) < 2:
            raise HTTPException(
                status_code=http_status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        token = tokens[1]
        try:
            # Verify the token against the Firebase Auth API.
            decoded_token = auth.verify_id_token(token)
        except FirebaseError:
            raise HTTPException(
                status_code=http_status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return decoded_token

'''
定义了一个简单的路由 /status，用于检查 API 的运行状态。当向该端点发送 GET 请求时，
将返回一个包含状态信息的 JSON 对象。'''
@router.get("/status")
async def status():
    return {"status": "ok", "message": "RealChar is running smoothly!"}

'''
/characters: GET 请求用于获取角色信息列表。首先检查是否设置了 Google Cloud Storage 的路径，然后从请求中获取当前用户的 UID。
接着从实时 AI 角色的目录管理器中获取角色信息，并根据用户权限和角色的可见性过滤结果，最后将结果返回为 JSON 格式。
'''
@router.get("/characters")
async def characters(user=Depends(get_current_user)):
    gcs_path = os.getenv("GCP_STORAGE_URL")
    if not gcs_path:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="GCP_STORAGE_URL is not set",
        )

    def get_image_url(character):
        if character.data and "avatar_filename" in character.data:
            return f'{gcs_path}/{character.data["avatar_filename"]}'
        else:
            return f"{gcs_path}/static/realchar/{character.character_id}.jpg"

    uid = user["uid"] if user else None
    from realtime_ai_character.character_catalog.catalog_manager import CatalogManager

    catalog: CatalogManager = CatalogManager.get_instance()
    return [
        {
            "character_id": character.character_id,
            "name": character.name,
            "source": character.source,
            "voice_id": character.voice_id,
            "author_name": character.author_name,
            "audio_url": f"{gcs_path}/static/realchar/{character.character_id}.mp3",
            "image_url": get_image_url(character),
            "tts": character.tts,
            "is_author": character.author_id == uid,
            "location": character.location,
            "rebyte_project_id": character.rebyte_api_project_id,
            "rebyte_agent_id": character.rebyte_api_agent_id,
        }
        for character in sorted(catalog.characters.values(), key=lambda c: c.order)
        if character.author_id == uid or character.visibility == "public"
    ]

'''
GET 请求用于获取配置信息，返回一个包含不同语言模型的列表。
'''
@router.get("/configs")
async def configs():
    return {
        "llms": ["gpt-4", "gpt-3.5-turbo-16k", "claude-2", "meta-llama/Llama-2-70b-chat-hf"],
    }

'''
GET 请求用于获取特定会话 ID 的交互历史记录，从数据库中读取交互历史记录，并将结果转换为 JSON 格式返回。
'''
@router.get("/session_history")
async def get_session_history(session_id: str, db: Session = Depends(get_db)):
    # Read session history from the database.
    interactions = await asyncio.to_thread(
        db.query(Interaction).filter(Interaction.session_id == session_id).all
    )
    # return interactions in json format
    interactions_json = [interaction.to_dict() for interaction in interactions]
    return interactions_json

'''
POST 请求用于提交反馈信息。首先检查用户身份验证，然后将反馈信息保存到数据库中。
'''
@router.post("/feedback")
async def post_feedback(
    feedback_request: FeedbackRequest, user=Depends(get_current_user), db: Session = Depends(get_db)
):
    if not user:
        raise HTTPException(
            status_code=http_status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    feedback = Feedback(**feedback_request.dict())
    feedback.user_id = user["uid"]
    feedback.created_at = datetime.datetime.now()  # type: ignore
    await asyncio.to_thread(feedback.save, db)

'''
POST 请求用于上传文件。首先检查用户身份验证，然后创建 Google Cloud Storage 客户端，并从请求中获取文件信息。
接着创建一个新的文件名，并将文件内容上传到指定的存储桶中，最后返回上传成功的文件信息。
'''
@router.post("/uploadfile")
async def upload_file(file: UploadFile = File(...), user=Depends(get_current_user)):
    if not user:
        raise HTTPException(
            status_code=http_status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    storage_client = storage.Client()
    bucket_name = os.environ.get("GCP_STORAGE_BUCKET_NAME")
    if not bucket_name:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="GCP_STORAGE_BUCKET_NAME is not set",
        )

    bucket = storage_client.bucket(bucket_name)

    # Create a new filename with a timestamp and a random uuid to avoid duplicate filenames
    file_extension = os.path.splitext(file.filename)[1] if file.filename else ""
    new_filename = (
        f"user_upload/{user['uid']}/"
        f"{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}-"
        f"{uuid.uuid4()}{file_extension}"
    )

    blob = bucket.blob(new_filename)

    contents = await file.read()

    await asyncio.to_thread(blob.upload_from_string, contents)

    return {"filename": new_filename, "content-type": file.content_type}

'''
POST 请求用于创建新的角色。首先验证用户身份，然后从请求中获取角色信息，并根据当前用户的 UID 将其设置为角色的作者 ID。
接着为角色生成一个新的 UUID，设置创建时间和更新时间，并将角色保存到数据库中。
'''
@router.post("/create_character")
async def create_character(
    character_request: CharacterRequest,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not user:
        raise HTTPException(
            status_code=http_status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    character = Character(**character_request.dict())
    character.id = str(uuid.uuid4().hex)  # type: ignore
    character.background_text = character_request.background_text  # type: ignore
    character.author_id = user["uid"]
    now_time = datetime.datetime.now()
    character.created_at = now_time  # type: ignore
    character.updated_at = now_time  # type: ignore
    await asyncio.to_thread(character.save, db)


'''
####这些路由处理函数负责角色信息的创建、编辑和删除操作，并在必要时进行身份验证和权限检查。
'''
'''
POST 请求用于编辑现有的角色信息。首先验证用户身份，然后从请求中获取要编辑的角色的 ID，并检查该角色是否存在以及当前用户是否有权限编辑该角色。
如果角色存在且用户有权限编辑，则从请求中获取新的角色信息，并更新角色的更新时间，然后将其合并到数据库中。
'''
@router.post("/edit_character")
async def edit_character(
    edit_character_request: EditCharacterRequest,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not user:
        raise HTTPException(
            status_code=http_status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    character_id = edit_character_request.id
    character = await asyncio.to_thread(
        db.query(Character).filter(Character.id == character_id).one
    )
    if not character:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Character {character_id} not found",
        )

    if character.author_id != user["uid"]:
        raise HTTPException(
            status_code=http_status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized to edit this character",
            headers={"WWW-Authenticate": "Bearer"},
        )
    character = Character(**edit_character_request.dict())
    character.updated_at = datetime.datetime.now()  # type: ignore
    db.merge(character)
    db.commit()

'''
POST 请求用于删除角色信息。首先验证用户身份，然后从请求中获取要删除的角色的 ID，
并检查该角色是否存在以及当前用户是否有权限删除该角色。如果角色存在且用户有权限删除，则将其从数据库中删除。
'''
@router.post("/delete_character")
async def delete_character(
    delete_character_request: DeleteCharacterRequest,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not user:
        raise HTTPException(
            status_code=http_status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    character_id = delete_character_request.character_id
    character = await asyncio.to_thread(
        db.query(Character).filter(Character.id == character_id).one
    )
    if not character:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Character {character_id} not found",
        )

    if character.author_id != user["uid"]:
        raise HTTPException(
            status_code=http_status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized to delete this character",
            headers={"WWW-Authenticate": "Bearer"},
        )
    db.delete(character)
    db.commit()
'''
###这个路由处理函数用于生成文本转语音的音频文件，并将其保存到 Google Cloud Storage (GCS) 中。'''
'''
首先，函数验证传入的文本是否为空，并检查用户是否已经通过身份验证。如果文本为空或用户未通过身份验证，则会引发相应的 HTTP 异常。
这段代码定义了一个 POST 请求的路由 /generate_audio，用于生成音频文件。该路由接收文本输入，并根据用户提供的文本使用文本转语音服务生成对应的音频文件。

与前端的交互主要体现在以下几个方面：

接收文本输入：路由函数中的 text: str 参数表示接收到的文本输入，这是前端发送的待转换成语音的文本内容。

处理身份验证：在路由函数中，首先对用户进行身份验证。如果用户未经过验证，将返回 401 错误给前端，表示未经授权。

选择文本转语音服务：根据用户提供的 tts 参数选择合适的文本转语音服务。如果未找到合适的服务，将返回 400 错误给前端，表示未找到文本转语音引擎。

生成音频文件：使用选定的文本转语音服务生成音频文件，并将其保存到 Google Cloud Storage 中。生成的音频文件将会在存储桶中以新的文件名和随机的 UUID 后缀保存。

返回响应数据：路由函数通过 return 语句将生成的音频文件信息返回给前端。返回的信息包括音频文件在存储桶中的路径和文件类型。

通过这些步骤，该路由实现了根据用户提供的文本生成音频文件，并将生成的音频文件路径返回给前端，完成了前后端的交互。
'''
@router.post("/generate_audio")
async def generate_audio(text: str, tts: Optional[str] = None, user=Depends(get_current_user)):
    if not isinstance(text, str) or text == "":
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Text is empty",
        )
    if not user:
        raise HTTPException(
            status_code=http_status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        tts_service = get_text_to_speech(tts)
    except NotImplementedError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Text to speech engine not found",
        )
    audio_bytes = await tts_service.generate_audio(text)
    # save audio to a file on GCS
    storage_client = storage.Client()
    bucket_name = os.environ.get("GCP_STORAGE_BUCKET_NAME")
    if not bucket_name:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="GCP_STORAGE_BUCKET_NAME is not set",
        )
    bucket = storage_client.bucket(bucket_name)

    # Create a new filename with a timestamp and a random uuid to avoid duplicate filenames
    file_extension = ".mp3"
    new_filename = (
        f"user_upload/{user['uid']}/"
        f"{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}-"
        f"{uuid.uuid4()}{file_extension}"
    )

    blob = bucket.blob(new_filename)

    await asyncio.to_thread(blob.upload_from_string, audio_bytes)

    return {"filename": new_filename, "content-type": "audio/mpeg"}

'''
是用于处理语音克隆和生成系统提示的.
这段代码实现了与前端的数据交换，通过接收文件列表并返回声音克隆结果，完成了前后端的交互。
'''
@router.post("/clone_voice")
async def clone_voice(filelist: list[UploadFile] = Form(...), user=Depends(get_current_user)):
    if not user:
        raise HTTPException(
            status_code=http_status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if len(filelist) > MAX_FILE_UPLOADS:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"Number of files exceeds the limit ({MAX_FILE_UPLOADS})",
        )

    storage_client = storage.Client()
    bucket_name = os.environ.get("GCP_STORAGE_BUCKET_NAME")
    if not bucket_name:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="GCP_STORAGE_BUCKET_NAME is not set",
        )

    bucket = storage_client.bucket(bucket_name)
    voice_request_id = str(uuid.uuid4().hex)

    for file in filelist:
        # Create a new filename with a timestamp and a random uuid to avoid duplicate filenames
        file_extension = os.path.splitext(file.filename)[1] if file.filename else ""
        new_filename = (
            f"user_upload/{user['uid']}/{voice_request_id}/"
            f"{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}-"
            f"{uuid.uuid4()}{file_extension}"
        )

        blob = bucket.blob(new_filename)

        contents = await file.read()

        await asyncio.to_thread(blob.upload_from_string, contents)

    # Construct the data for the API request
    # TODO: support more voice cloning services.
    data = {
        "name": user["uid"] + "_" + voice_request_id,
    }

    files = [("files", (file.filename, file.file)) for file in filelist]

    headers = {
        "xi-api-key": os.getenv("ELEVEN_LABS_API_KEY", ""),
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.elevenlabs.io/v1/voices/add", headers=headers, data=data, files=files
        )

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)

    return response.json()


@router.post("/system_prompt")
async def system_prompt(request: GeneratePromptRequest, user=Depends(get_current_user)):
    """Generate System Prompt according to name and background."""
    name = request.name
    background = request.background
    if not isinstance(name, str) or name == "":
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Name is empty",
        )
    if not user:
        raise HTTPException(
            status_code=http_status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"system_prompt": await generate_system_prompt(name, background)}

'''
提供了对话记录查询、角色信息获取和突出显示生成功能的后端支持。
'''
'''
与前端有交互接收 HTTP 请求并返回相应的数据或错误响应'''
@router.get("/conversations", response_model=list[dict])
async def get_recent_conversations(user=Depends(get_current_user), db: Session = Depends(get_db)):
    if not user:
        raise HTTPException(
            status_code=http_status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = user["uid"]
    stmt = (
        db.query(
            Interaction.session_id,
            Interaction.client_message_unicode,
            Interaction.timestamp,
            func.row_number()
            .over(partition_by=Interaction.session_id, order_by=Interaction.timestamp.desc())
            .label("rn"),
        )
        .filter(Interaction.user_id == user_id)
        .subquery()
    )

    results = await asyncio.to_thread(
        db.query(stmt.c.session_id, stmt.c.client_message_unicode)
        .filter(stmt.c.rn == 1)
        .order_by(stmt.c.timestamp.desc())
        .all
    )

    # Format the results to the desired output
    return [
        {"session_id": r[0], "client_message_unicode": r[1], "timestamp": r[2]} for r in results
    ]

'''
与前端有交互'''
@router.get("/get_character")
async def get_character(
    character_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)
):
    if not user:
        raise HTTPException(
            status_code=http_status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    character = await asyncio.to_thread(
        db.query(Character).filter(Character.id == character_id).one
    )
    if not character:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Character {character_id} not found",
        )
    if character.author_id != user["uid"]:
        raise HTTPException(
            status_code=http_status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized to access this character",
            headers={"WWW-Authenticate": "Bearer"},
        )
    character_json = character.to_dict()
    return character_json

'''
与前端有交互
定义了一个 GenerateHighlightRequest 类型的请求体，用于接收前端发送的上下文和提示信息。
前端通过向该端点发送 POST 请求并提供相应的请求体来与后端交互。'''
@router.post("/generate_highlight")
async def generate_highlight(
    generate_highlight_request: GenerateHighlightRequest, user=Depends(get_current_user)
):
    # Only allow for authorized user.
    if not user:
        raise HTTPException(
            status_code=http_status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    context = generate_highlight_request.context
    prompt = generate_highlight_request.prompt
    result = ""
    if prompt:
        result = await generate_highlight_based_on_prompt(context, prompt)
    else:
        result = await generate_highlight_action(context)

    return {"highlight": result}
