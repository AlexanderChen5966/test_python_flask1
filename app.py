import os
from flask import Flask, request, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
from flasgger import Swagger
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from datetime import datetime
from dotenv import load_dotenv


# 初始化 Flask 應用
app = Flask(__name__)
load_dotenv()  # 會自動從根目錄的 .env 檔載入變數

# 設定資料庫配置（MySQL）
# Flasgger文件網址: https://testpythonflask1-production.up.railway.app/apidocs
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('MYSQL_PUBLIC_URL')  # 設定 MySQL 資料庫 URI（從 Railway 取得）
# app.config['SQLALCHEMY_DATABASE_URI'] = "mysql://root:LepIwlpQcMsIqKKSMMrSbpSasaEDLywE@caboose.proxy.rlwy.net:56460/railway"
# app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://root:WWMfPkrHYAFzMKjWMKsyPSacMJBjVIIo@interchange.proxy.rlwy.net:58470/railway'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# 設定 LINE API 的 Token 和 Secret
# line
# https://testpythonflask1-production.up.railway.app/callback
# LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
# LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET')

# Channel ID  1567481099
# LINE_CHANNEL_SECRET:39a8506293131666215364ce4a6cffeb
# Channel access token: eilzTMbjJ5eW0VUGlFNXnp6ofs8XfekOSnbW513ktpCNaNZSImAChjyP7fOB5G9u0eagtJrNtGInHzffSyWg/9OiX8ZVznj8/rPbDcrCIPbf5wTfaV1rJOHCvFS8sKZu667TqsT7lQFtJ64qRexUxQdB04t89/1O/w1cDnyilFU=
LINE_CHANNEL_SECRET = "39a8506293131666215364ce4a6cffeb"
LINE_CHANNEL_ACCESS_TOKEN = "eilzTMbjJ5eW0VUGlFNXnp6ofs8XfekOSnbW513ktpCNaNZSImAChjyP7fOB5G9u0eagtJrNtGInHzffSyWg/9OiX8ZVznj8/rPbDcrCIPbf5wTfaV1rJOHCvFS8sKZu667TqsT7lQFtJ64qRexUxQdB04t89/1O/w1cDnyilFU="
# 初始化 LINE Bot API 和 WebhookHandler
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# 初始化 Flasgger
swagger = Swagger(app)


# 定義資料庫模型

# 用戶資料表格
class User(db.Model):
    user_id = db.Column(db.Integer, primary_key=True)
    line_user_id = db.Column(db.String(255), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# 打卡紀錄資料表格
class Checkin(db.Model):
    checkin_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)
    checkin_time = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref=db.backref('checkins', lazy=True))


# LINE 回覆資料表格
class LineReply(db.Model):
    reply_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)
    reply_message = db.Column(db.Text, nullable=False)
    reply_time = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref=db.backref('line_replies', lazy=True))


# 設計 POST /api/checkin API
@app.route('/api/checkin', methods=['POST'])
def checkin():
    """
    User check-in API
    ---
    parameters:
      - name: line_user_id
        in: json
        type: string
        required: true
        description: LINE user ID
    responses:
      200:
        description: "Check-in successful"
        schema:
          type: object
          properties:
            message:
              type: string
              example: "You have successfully checked in!"
    """
    data = request.get_json()
    line_user_id = data.get('line_user_id')

    # 查找用戶
    user = User.query.filter_by(line_user_id=line_user_id).first()

    if not user:
        return jsonify({"message": "User not found"}), 404

    # 儲存打卡紀錄
    checkin = Checkin(user_id=user.user_id)
    db.session.add(checkin)
    db.session.commit()

    return jsonify({"message": "You have successfully checked in!"})


# 設計 GET /api/checkins/{user_id} API
@app.route('/api/checkins/<int:user_id>', methods=['GET'])
def get_checkins(user_id):
    """
    Get check-ins of a user
    ---
    parameters:
      - name: user_id
        in: path
        type: integer
        required: true
        description: User ID
    responses:
      200:
        description: "User check-ins found"
        schema:
          type: object
          properties:
            checkins:
              type: array
              items:
                type: object
                properties:
                  checkin_id:
                    type: integer
                  checkin_time:
                    type: string
                    format: date-time
    """
    checkins = Checkin.query.filter_by(user_id=user_id).all()
    checkin_list = [
        {"checkin_id": checkin.checkin_id, "checkin_time": checkin.checkin_time.isoformat()}
        for checkin in checkins
    ]

    return jsonify({"checkins": checkin_list})


# 設計 POST /api/line_reply API
@app.route('/api/line_reply', methods=['POST'])
def line_reply():
    """
    Reply to a user in LINE
    ---
    parameters:
      - name: user_id
        in: json
        type: integer
        required: true
        description: User ID
      - name: reply_message
        in: json
        type: string
        required: true
        description: Message to reply to the user
    responses:
      200:
        description: "Reply sent successfully"
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Reply sent successfully!"
    """
    data = request.get_json()
    user_id = data.get('user_id')
    reply_message = data.get('reply_message')

    # 查找用戶
    user = User.query.filter_by(user_id=user_id).first()

    if not user:
        return jsonify({"message": "User not found"}), 404

    # 儲存LINE回覆
    reply = LineReply(user_id=user_id, reply_message=reply_message)
    db.session.add(reply)
    db.session.commit()

    return jsonify({"message": "Reply sent successfully!"})

# 註冊使用者 API
@app.route('/api/register', methods=['POST'])
def register_user():
    """
    Register a new LINE user
    ---
    parameters:
      - name: line_user_id
        in: json
        type: string
        required: true
        description: LINE user ID
      - name: name
        in: json
        type: string
        required: true
        description: Name of the user
    responses:
      200:
        description: User registration result
        schema:
          type: object
          properties:
            message:
              type: string
    """
    data = request.get_json()
    line_user_id = data.get('line_user_id')
    name = data.get('name')

    if not line_user_id or not name:
        return jsonify({"message": "Missing line_user_id or name"}), 400

    # 檢查用戶是否已存在
    existing_user = User.query.filter_by(line_user_id=line_user_id).first()

    if existing_user:
        return jsonify({"message": "User already registered"}), 200

    # 新增用戶
    new_user = User(line_user_id=line_user_id, name=name)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "User registered successfully"}), 201


# 設置 LINE Webhook 路由
@app.route("/callback", methods=["POST"])
def callback():
    # 確保是 LINE 發來的請求
    if request.headers["X-Line-Signature"] is None:
        abort(400)

    body = request.get_data(as_text=True)
    signature = request.headers["X-Line-Signature"]
    handler.handle(body, signature)

    return 'OK', 200


# 處理 LINE 訊息
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    line_user_id = event.source.user_id

    # 檢查用戶是否存在
    user = User.query.filter_by(line_user_id=line_user_id).first()

    if not user:
        # 如果用戶不存在，就從 LINE API 拿名字並註冊
        try:
            profile = line_bot_api.get_profile(line_user_id)
            display_name = profile.display_name
        except Exception as e:
            print("Error fetching profile:", e)
            display_name = "LINE User"

        new_user = User(line_user_id=line_user_id, name=display_name)
        db.session.add(new_user)
        db.session.commit()

        reply_text = f"歡迎你，{display_name}！你已完成註冊 ✅"
    else:
        # 如果用戶已存在，就打招呼
        reply_text = f"歡迎回來，{user.name}！你已成功打卡 ✅"

        # 也可以順便自動記一筆打卡紀錄
        checkin = Checkin(user_id=user.user_id)
        db.session.add(checkin)
        db.session.commit()

    # 回覆使用者訊息
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

# @handler.add(MessageEvent, message=TextMessage)
# def handle_message(event):
#     # 回覆用戶訊息
#     line_bot_api.reply_message(
#         event.reply_token,
#         TextMessage(text='You have successfully checked in!')
#     )


# 啟動 Flask 應用
if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # 建立資料表
    app.run(host='0.0.0.0')