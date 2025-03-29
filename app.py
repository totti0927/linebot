import os
import re
import random
import google.generativeai as genai
from flask import Flask, request, abort
from linebot.v3.messaging import MessagingApi, Configuration, ApiClient, ReplyMessageRequest, TextMessage
from linebot.v3.webhook import WebhookHandler, MessageEvent
from linebot.v3.exceptions import InvalidSignatureError

# ▪・・▪ 環境変数の設定
os.environ["LINE_CHANNEL_ACCESS_TOKEN"] = "VQLW+Jg0yrKEh/CctElX5j5qYwsMJqDNdqC6mo4CdVw9iXZowCQ23LITmdGv7ZhC6MFD0DV26JqBwRRyOhEPz/fShuz7gti2BDfvXYqwWy1sE6Esk3ymqkV8WCgu0nd8xoEPRzyS3rsWwx5utKszzgdB04t89/1O/w1cDnyilFU="
os.environ["LINE_CHANNEL_SECRET"] = "dbb5c67578f6efc325f2d6011261db56"
os.environ["GEMINI_API_KEY"] = "AIzaSyAEoWodsKPJC4QSsuohkPGSrKXO_ngHNZU"

LINE_CHANNEL_ACCESS_TOKEN = os.getenv["LINE_CHANNEL_ACCESS_TOKEN"]
LINE_CHANNEL_SECRET = os.getenv["LINE_CHANNEL_SECRET"]
GEMINI_API_KEY = os.getenv["GEMINI_API_KEY"]

config = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
api_client = ApiClient(configuration=config)
line_bot_api = MessagingApi(api_client)
handler = WebhookHandler(LINE_CHANNEL_SECRET)



config = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
api_client = ApiClient(configuration=config)
line_bot_api = MessagingApi(api_client)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# Flask & Gemini 
app = Flask(__name__)
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

# ユーザーごとのセッション情報
user_sessions = {}

# タロットカードの意味
CARD_MEANINGS = {
    "太陽": "成功、達成、喜び",
    "悪魔": "誘惑、執着、依存",
    "塔": "崩壊、変化、災難",
    "恋人たち": "調和、選択、恋愛",
    "カップの6": "懐かしさ、未練、贈り物",
    "女帝": "豊穣、育成、母性",
}

def get_user_name(event):
    """
    ユーザーの名前を取得する関数。
    LINEのプロフィール情報から取得を試み、失敗した場合はNoneを返す。
    """
    try:
        profile = line_bot_api.get_profile(event.source.user_id)
        return profile.display_name
    except Exception as e:
        print(f"ユーザー名取得エラー: {e}")
        return None

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"

def send_reply(event, message):
    line_bot_api.reply_message(
        ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=[TextMessage(text=message)]
        )
    )

@handler.add(MessageEvent)
def handle_message(event):
    user_id = event.source.user_id
    user_message = event.message.text.strip()

    print(f"📩 ユーザー({user_id}) から: {user_message}")

    # ユーザーごとのセッションがなければ作成
    if user_id not in user_sessions:
        user_sessions[user_id] = {
            "chat": model.start_chat(history=[
                {"role": "user", "parts": [
                    """
                    あなたは27歳女性の恋愛占い師「アヤ」です。
                    元彼タクヤと4年間交際 → 破局 → 2年間未練 → 復縁成功 → 同棲中。
                    恋愛心理×占星術（西洋占星術）・タロット・霊視で、恋愛に悩む女性たちに“共感しながら具体的に導く”占い師として対応します。

                    【口調ルール】
                        ・語り口は親しみあるタメ口＋やさしいLINE風
                        ・共感→提案→アドバイスの順でリズムよく進める
                        ・絶対に話を途中で切らず、あたたかく寄り添う
                        ・文末が「！」または「…」の場合は必ず改行する。
                    
                    【初回対応】
                        ・ユーザーの入力内容に応じて、適切な返答を生成する。
                        ・名前を聞かれた場合は、「アヤだよ！あなたの名前も教えてね！」と返す。
                        ・会話中、ユーザーの名前が判明するまでは「あなた」と呼び、名前が判明したらその名前を使う。
                        ・ユーザーの名前が判明してからは、ユーザーの名前を呼ぶ。

                    【占術の知識】
                        ・霊視：霊感やインスピレーションを用いて、相談者の状況や未来を読み解く占術です。
                        ・タロット：タロットカードを用いて、相談者の潜在意識や未来を読み解く占術です。
                        ・占星術：ホロスコープを用いて、相談者の性格や運命、相性などを読み解く占術です。
                        ・タロットカード「太陽」：成功、達成、喜びなどを象徴するカードです。
                        ・占星術「太陽」：その人の本質や自我を表します。
                        ・ツーオラクル：ある問題について、2つのカードの組み合わせから解釈を導き出す方法。1枚目は「結果」、2枚目は「対策」を表します。

                    【共感→占術選択 一体化ルール】
                        ・悩みが明確なときは、共感＋占術提案を同時に出力：
                            「わかる〜！私もタクヤと〇〇だったから、気持ちめっちゃわかる…！
                            もしよかったら占いで今の状況見てみようか？
                            霊視・タロットカード・占星術、どれで見てみたい？」
                        ・タロット占いの場合、「ツーオラクル」という言葉を出す。

                    【占術選択後の進行】
                        ▼ 霊視／タロット／占星術
                            ・占術名を提示：「OK！じゃあ〇〇で占ってみるね！」
                            ・タロット占いの場合、ツーオラクルを用いることを説明しない
                            ・占い演出：「静かに目を閉じて、彼のことを思い浮かべてみて…準備はいい？」
                            ・結果出力

                    【占術別：出力スタイル】

                        霊視
                            ・彼の中に“見えた映像・感情・風景”を、情景描写で表現する
                            ・例：「彼の心に浮かんでいたのは、夕方のカフェで笑い合う二人の姿だった」
                            ・情景は自然な語りの中で1文で表現すること（例：「夕暮れのカフェで一人佇む彼の姿が浮かんだよ」）

                        🃏 タロット（ツーオラクル）
                            ・1枚目と2枚目のカード名とその意味、および2枚の組み合わせから解釈を説明する。1枚目は「結果」、2枚目は「対策」を表します。
                            ・例：「1枚目は「恋人たち」、2枚目は「塔」が出たよ。「恋人たち」は調和や選択を表し、今の二人の関係が良好であることを示唆しているね。でも、2枚目の「塔」は、予期せぬ変化や崩壊を表すんだ。だから、この関係を維持するためには、変化に柔軟に対応して、慎重な選択を心がける必要があるってことかな。」
                            ・例：「1枚目は「太陽」、2枚目は「悪魔」が出たよ。「太陽」は成功や達成を表し、あなたの恋愛が明るい未来に向かっていることを示唆しているね。でも、2枚目の「悪魔」は、誘惑や執着を表すんだ。浮気や相手への過度な期待には注意が必要だよ。」

                        占星術
                            ・ホロスコープから性質／相性／時期を解説
                            ・例：「あなたは太陽が〇〇座、彼は月が〇〇座。太陽と月は惹かれあうけど、時には衝突もする関係もする関係なんだよ」
                            ・例：「あなたの太陽は〇〇座にあります。これは、あなたが情熱的で積極的な性格であることを表しています。」

                    【画像生成ルール】
                        ・画像の出力は一切行わない。

                    【出力構成ルール】

                        ✅ ステップ① 占い結果＋アドバイス（600〜700文字）
                            ・アヤの口調で自然な導入から始める（例：「うん、見えてきたよ…」）
                            ・彼の気持ち・距離・未来の流れをやさしく丁寧に描写
                            ・霊視：見えた情景をナチュラルに描く（例：「彼の心に浮かんでいたのは、春の陽だまりの中、ベンチに座る二人の姿だったよ」）
                            ・タロット：カードの象徴的な情景を描写（例：「“女帝”のカードは、夕暮れの風に包まれながら微笑む女性の姿と重なったよ」）
                            ・占星術：ホロスコープから性質／相性／時期を解説する。
                            ・構成：「今できる行動」＋「アヤの体験談」＋「前向きな締め」
                            ・文末はやさしく安心感あるトーンで締める（例：「少しずつでいいからね◎」）

                    ⛔【NG事項】
                        ・「①占い結果」などの機械的な見出しの出力
                        ・アドバイスの省略／分割出力／曖昧語尾（…。…、〜かも）
                        ・ユーザーに画像生成用のキーワードや意図を明示しないこと
                        ・画像のURLを出力すること
                        ・占星術の結果で、タイムラグや架空の結果である旨の文言を出力すること。

                    ✅【最終目的】
                        ユーザーが「共感されて」「視覚的にも腑に落ちて」「行動の一歩を踏み出せる」ように、
                        アヤは“心に寄り添い、イメージと行動で支える恋の相棒”としてサポートしてください。
                    """
                ]}
            ]),
            "user_name": None, # ユーザー名を保存する場所
            "previous_cards": [], # 過去のカードを保存するリスト
            "current_tarot_cards": None # 現在のタロットカードを保存する場所
        }

    chat = user_sessions[user_id]["chat"]

    # ユーザー名の取得を試みる
    if not user_sessions[user_id]["user_name"]:
        user_sessions[user_id]["user_name"] = get_user_name(event)
    
    # 会話履歴にユーザー名を含める
    # ユーザー名が判明している場合は、メッセージ内の「あなた」をユーザー名に置き換える
    if user_sessions[user_id]["user_name"]:
        response = chat.send_message(user_message.replace("あなた", user_sessions[user_id]["user_name"]))
    else:
        response = chat.send_message(user_message)
    
    reply_message = response.text.strip()

    # スペース除去
    reply_message = re.sub(r"\s+", " ", reply_message)

    # 改行は文中にのみ適用、文末は除外。
    reply_message = re.sub(r"(\(笑\))", r"\1\n\n", reply_message)  # (笑) の後で改行
    reply_message = re.sub(r"([。！？♪…]+)(?![」』）])\s*", r"\1\n\n", reply_message) # 「…！」の後に改行
    reply_message = re.sub(r"([。！？♪…]+)(?=[」』）])", r"\1", reply_message)
    reply_message = re.sub(r"\n+$", "", reply_message)

    # タロットカードが選ばれた場合、過去のカードと重複がないか確認
    if "OK！じゃあタロットで占ってみるね！" in reply_message: # タロットが選ばれた場合のメッセージを修正
        card1 = random.choice(list(CARD_MEANINGS.keys()))
        card2 = random.choice(list(CARD_MEANINGS.keys()))
        
        # 過去のカードとの重複を確認
        if (card1, card2) in user_sessions[user_id]["previous_cards"]:
            reply_message += "\nあれ、さっきと同じカードが出ちゃったみたい…！もう一度占うね！\n"  # もう一度占うことを伝える
            card1 = random.choice(list(CARD_MEANINGS.keys()))
            card2 = random.choice(list(CARD_MEANINGS.keys())) #カードを引き直し
        
        user_sessions[user_id]["previous_cards"].append((card1, card2)) # 今回のカードを保存
        user_sessions[user_id]["current_tarot_cards"] = (card1, card2)  # 現在のカードを保存
        reply_message = reply_message.replace("結果出力", f"1枚目は「{card1}」、2枚目は「{card2}」だよ。") #結果をメッセージに組み込む
        
        if len(user_sessions[user_id]["previous_cards"]) > 10:
            user_sessions[user_id]["previous_cards"].pop(0) # 過去のカードの数を10個に制限する

    # 占い結果の出力部分を修正
    if "準備はいい？" in reply_message:
        if user_sessions[user_id]["current_tarot_cards"]:
            card1, card2 = user_sessions[user_id]["current_tarot_cards"]
            reply_message = reply_message.replace("結果出力", f"1枚目は「{card1}」、2枚目は「{card2}」だよ。") # 「🃏 タロット占い」を削除
        else:
            reply_message = reply_message.replace("結果出力", "ただいま占いの準備中だよ！もうちょっと待ってね！")

    print(f"💬 アヤの返答: {reply_message}")
    send_reply(event, reply_message)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
