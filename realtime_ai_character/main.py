import warnings

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from realtime_ai_character.audio.speech_to_text import get_speech_to_text
from realtime_ai_character.audio.text_to_speech import get_text_to_speech
from realtime_ai_character.character_catalog.catalog_manager import CatalogManager
from realtime_ai_character.restful_routes import router as restful_router
from realtime_ai_character.twilio.websocket import twilio_router
from realtime_ai_character.utils import ConnectionManager
from realtime_ai_character.websocket_routes import router as websocket_router

'''
使用 FastAPI() 创建一个 FastAPI 应用程序实例，并将其存储在变量 app 中。
'''
app = FastAPI()
'''添加 CORS 中间件
使用 app.add_middleware() 方法添加 CORS 中间件，以允许跨域资源共享。
配置了一些允许的选项，如允许的来源、允许的方法和允许的头部。
'''
app.add_middleware(
    CORSMiddleware,
    # Change to domains if you deploy this to production
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
'''
包含路由器：
使用 app.include_router() 方法包含不同的路由器，分别是 restful_router、websocket_router 
和 twilio_router。
'''
app.include_router(restful_router)
app.include_router(websocket_router)
app.include_router(twilio_router)


# initializations
'''
初始化：
调用 CatalogManager.initialize() 和 ConnectionManager.initialize() 方法来初始化目录管理器和连接管理器。
调用 get_text_to_speech() 和 get_speech_to_text() 方法来初始化文本到语音和语音到文本功能。

restful_router：
这个路由器用于处理 RESTful API 风格的请求，即使用 HTTP 方法（如 GET、POST、PUT、DELETE 等）来对资源进行 CRUD（创建、读取、更新、删除）操作。
RESTful API 是一种常见的设计风格，用于构建易于理解和使用的 Web 服务接口。
在这个路由器中，可能会定义一些端点来处理用户账户、文章、评论等资源的增删改查操作。

websocket_router：
这个路由器用于处理 WebSocket 连接的请求。
WebSocket 是一种在客户端和服务器之间建立持久连接的协议，可以实现双向通信，而不像 HTTP 协议那样每次请求都需要建立新的连接。
WebSocket 路由器通常用于实时通信场景，如聊天应用、实时数据更新等。

twilio_router：
这个路由器用于处理 Twilio 平台的请求。
Twilio 是一家提供云通信平台的服务商，可以用于发送短信、语音、视频等。
Twilio 路由器可能用于与 Twilio 平台进行集成，处理来自 Twilio 的消息和通话请求。
'''
CatalogManager.initialize()
ConnectionManager.initialize()
get_text_to_speech()
get_speech_to_text()

# suppress deprecation warnings
'''使用 warnings.filterwarnings() 方法来忽略特定模块中的警告信息。'''

warnings.filterwarnings("ignore", module="whisper")
if __name__ == "__main__":
    '''
    使用 uvicorn.run() 方法运行 FastAPI 应用程序，指定了主机地址和端口号。
    '''
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
# 这里的192.168.43.168需要替换为自己的主机地址

