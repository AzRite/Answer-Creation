from flask import Flask, request, abort
import os

#JSONファイルを扱うのに必要
import json

#ユーザー情報の取得に必要
import urllib

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, MemberJoinedEvent,
)

app = Flask(__name__)

#環境変数取得
YOUR_CHANNEL_ACCESS_TOKEN = os.environ["YOUR_CHANNEL_ACCESS_TOKEN"]
YOUR_CHANNEL_SECRET = os.environ["YOUR_CHANNEL_SECRET"]

line_bot_api = LineBotApi(YOUR_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(YOUR_CHANNEL_SECRET)

@app.route("/")
def hello_world():
    return "hello world!"

@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

#オウム返し（テスト用）
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=event.message.text))

#ユーザーネームを含んだ挨拶
@handler.add(MemberJoinedEvent)
def handle_join(event):
    #参加イベント情報から「ユーザーID」と「グループID」を取得
    uId = event.joined.members[0].user_id
    gId = event.source.group_id
    #LINEのAPIから「ユーザーID」と「グループID」をもとに「ユーザー情報」を取得
    url = 'https://api.line.me/v2/bot/group/{}/member/{}'.format(gId, uId);
    headers = {
        'Content-Type': 'application/json; charset=UTF-8',
        'Authorization': 'Bearer ' + YOUR_CHANNEL_ACCESS_TOKEN,
    }

    req = urllib.request.Request(url, None, headers)
    with urllib.request.urlopen(req) as res:
        response = res.read()
    json_result = json.loads(response.decode('utf-8'))
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text="こんにちは、{}".format(json_result["displayName"])))



if __name__ == "__main__":
#    app.run()
    port = int(os.getenv("PORT"))
    app.run(host="0.0.0.0", port=port)
