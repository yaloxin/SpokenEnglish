import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
# 这段代码的作用就是配置数据库连接，并提供了一种获取数据库会话对象的方法，以便在应用程序中执行数据库操作。

# 调用了load_dotenv()函数来加载环境变量，这个函数通常用于从.env文件中加载环境变量
load_dotenv()
# 这行代码从环境变量中获取数据库连接字符串。它使用了os.getenv()函数来获取名为DATABASE_URL的环境变量的值，
# 如果该环境变量不存在，则使用空字符串作为默认值。
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "")
'''
这行代码根据数据库连接字符串的类型设置连接参数。如果数据库是SQLite类型，
则设置check_same_thread参数为False，以避免在多线程环境中出现错误。
'''
connect_args = {"check_same_thread": False} if SQLALCHEMY_DATABASE_URL.startswith("sqlite") else {}
'''
代码使用create_engine函数创建了一个数据库引擎对象。
该对象用于与数据库进行通信，执行SQL语句等操作。它接受数据库连接字符串和连接参数作为参数。
'''
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=connect_args)
'''
这行代码使用sessionmaker函数创建了一个会话类SessionLocal。
会话对象用于在应用程序中执行数据库操作。在这里，我们指定了一些参数，如autocommit=False和autoflush=False，
以及绑定了之前创建的数据库引擎。
'''
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 生成器函数get_db()，用于获取数据库会话对象
def get_db():
    # 建了一个数据库会话对象db
    db = SessionLocal()
    try:
        # 使用yield语句将会话对象db返回给调用方
        yield db
    finally:
        # 在try块结束时关闭数据库会话对象
        db.close()


if __name__ == "__main__":
    print(SQLALCHEMY_DATABASE_URL)
    from realtime_ai_character.models.user import User

    with SessionLocal() as session:
        print(session.query(User).all())
        session.delete(User(name="Test", email="text@gmail.com"))
        session.commit()

        print(session.query(User).all())
        session.query(User).filter(User.name == "Test").delete()
        session.commit()

        print(session.query(User).all())
