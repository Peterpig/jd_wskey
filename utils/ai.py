import os
import time

from openai import OpenAI


class AI:

    def __init__(self):
        self.client = OpenAI(
            base_url=os.getenv("AI_BASE_URL"), api_key=os.getenv("AI_API_KEY")
        )

    def chat(self, detail, base64_image):
        # 自定义人设
        system_prompt = """
            你是一个专业的图片识别机器人，请根据用户提供的图片和内容进行识别，并给出识别结果。
            你需要根据图片和内容进行识别，需要识别用户给到你的4个中文汉字，在图片中的坐标。
            例如用户输入， 勇往直前， 你则直接返回 这4个汉字在图片中的坐标。
            识别结果以 JSON 的形式输出，输出的 JSON 需遵守以下的格式：
            {
                "status": "success",
                "results": {
                    "汉字1": "坐标1",
                    "汉字2": "坐标2",
                    "汉字3": "坐标3",
                    "汉字4": "坐标4"
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
                        "type": "text",
                        "text": {detail},
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                    },
                ],
            },
        ]

        try:
            completion = self.client.chat.completions.create(
                model=os.getenv("AI_MODEL"),
                messages=messages,
                temperature=0.3,
                response_format={"type": "json_object"},
            )
        except Exception as e:
            return '{"status": "fail", "message": "识别不到对应的文字"}'

        return completion.choices[0].message.content
