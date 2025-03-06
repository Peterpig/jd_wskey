import os
import json
import base64

from openai import OpenAI

base_url = os.getenv("AI_BASE_URL")
api_key = os.getenv("AI_API_KEY")
model = os.getenv("AI_MODEL")

class AI:

    def __init__(self):
        self.client = OpenAI(
            base_url=base_url, api_key=api_key
        )

    def chat(self, detail, base64_image_path):
        base64_image = encode_image(base64_image_path)

        # 自定义人设
        system_prompt = """
            你是一个专业的图片识别机器人，请根据用户提供的图片(275px*170px)和内容进行识别，并给出识别结果。
            例如用户输入， 勇往直前， 你则直接返回 这4个汉字在图片中相对于左上角（0,0）的坐标。这个坐标要是该字体中间位置的坐标。同时，以base64_image为基础，将红点绘制在图片上。
            识别结果以 JSON 的形式输出，输出的 JSON 需遵守以下的格式：
            {
                "status": "success",
                "results": {
                    "勇": "10,150",
                    "往": "20,200",
                    "直": "30,100",
                    "前": "300,100"
                }
            },
            如果你识别不到对应的文字，请返回：
            {
                "status": "fail",
                "message": "识别不到对应的文字"
            }
        """

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpg;base64,{base64_image}"},
                    },
                    {
                        "type": "text",
                        "text": f"{detail}",
                    },
                ],
            },
        ]

        try:
            completion = self.client.chat.completions.create(
                model=model,
                messages=messages,
                response_format = { "type": "json_object" },
            )
            return json.loads(completion.choices[0].message.content)
        except Exception as e:
            return json.dumps({"status": "fail", "message": f"识别不到对应的文字{str(e)}"}, ensure_ascii=False)




def encode_image(image_path):
  with open(image_path, "rb") as image_file:
    return base64.b64encode(image_file.read()).decode('utf-8')

if __name__ == "__main__":
    ai = AI()
    res = ai.chat("精神焕发", "/home/hello/workspace/jd_wskey/images/20250211080927_cpc.jpg")

    print(res)
    print(type(res))
