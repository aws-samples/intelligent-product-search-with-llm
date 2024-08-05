from typing import Dict, Any
import json
import warnings
HUMAN_PROMPT = "\n\nHuman:"
ASSISTANT_PROMPT = "\n\nAssistant:"
ALTERNATION_ERROR = (
    "Error: Prompt must alternate between '\n\nHuman:' and '\n\nAssistant:'."
)
class BedrockAdapter:
    @classmethod
    def _add_newlines_before_ha(cls,input_text: str) -> str:
        new_text = input_text
        for word in ["Human:", "Assistant:"]:
            new_text = new_text.replace(word, "\n\n" + word)
            for i in range(2):
                new_text = new_text.replace("\n\n\n" + word, "\n\n" + word)
        return new_text

    @classmethod
    def _human_assistant_format(cls,input_text: str) -> str:
        if input_text.count("Human:") == 0 or (
                input_text.find("Human:") > input_text.find("Assistant:")
                and "Assistant:" in input_text
        ):
            input_text = HUMAN_PROMPT + " " + input_text  # SILENT CORRECTION
        if input_text.count("Assistant:") == 0:
            input_text = input_text + ASSISTANT_PROMPT  # SILENT CORRECTION
        if input_text[: len("Human:")] == "Human:":
            input_text = "\n\n" + input_text
        input_text = cls._add_newlines_before_ha(input_text)
        count = 0
        # track alternation
        for i in range(len(input_text)):
            if input_text[i : i + len(HUMAN_PROMPT)] == HUMAN_PROMPT:
                if count % 2 == 0:
                    count += 1
                else:
                    warnings.warn(ALTERNATION_ERROR + f" Received {input_text}")
            if input_text[i : i + len(ASSISTANT_PROMPT)] == ASSISTANT_PROMPT:
                if count % 2 == 1:
                    count += 1
                else:
                    warnings.warn(ALTERNATION_ERROR + f" Received {input_text}")

        if count % 2 == 1:  # Only saw Human, no Assistant
            input_text = input_text + ASSISTANT_PROMPT  # SILENT CORRECTION

        return input_text
    
    @classmethod
    def prepare_output(cls, provider: str, response: Any) -> str:
        if provider == "anthropic":
            response_body = json.loads(response.get("body").read().decode())
            if 'content' in response_body.keys():
                return response_body.get("content")[0].get("text")
            else:
                return response_body.get("completion")
        else:
            response_body = json.loads(response.get("body").read())

        if provider == "ai21":
            return response_body.get("completions")[0].get("data").get("text")
        elif provider == "cohere":
            return response_body.get("generations")[0].get("text")
        elif provider == "meta":
            return response_body.get("generation")
        elif provider == "mistral":
            return response_body.get("outputs")[0].get("text")
        else:
            return response_body.get("results")[0].get("outputText")    
    
    
    @classmethod
    def prepare_input(
            cls, provider: str, prompt: str, model_kwargs: Dict[str, Any]
    ) -> Dict[str, Any]:
        kwargs = {**model_kwargs}

        max_tokens=512
        if "max_tokens" in kwargs.keys():
            max_tokens = int(kwargs['max_tokens'])
        # print('max_tokens:',max_tokens)

        modelId = 'anthropic.claude-v2'
        if "modelId" in kwargs.keys():
            modelId = kwargs['modelId']
        # print('modelId:',modelId)

        temperature=0.01
        if "temperature" in kwargs.keys():
            temperature = float(kwargs['temperature'])
        # print('temperature:',temperature)
        
        language='chinese'
        if "language" in kwargs.keys():
            language = kwargs['language']
        # print('language:',language)

        if modelId.find('claude-v2') >=0 or modelId.find('claude-instant') >=0:
            prompt = cls._human_assistant_format(prompt)
            input_body = {"prompt": prompt, "max_tokens_to_sample": max_tokens,"temperature": temperature}
        elif modelId.find('claude-3') >=0:

            input_body = {
                "anthropic_version": "bedrock-2023-05-31"
            }
            if int(max_tokens) > 0:
                input_body['max_tokens'] = max_tokens
            if float(temperature) > 0:
                input_body['temperature'] = temperature

            if 'system' in model_kwargs.keys():
                input_body['system'] = model_kwargs['system']

            input_body['messages'] = []

            messages = {}
            messages['role'] = 'user'
            messages['content'] = []

            if 'image' in model_kwargs.keys():
                image_dic = {"type": "image"}
                source = {"type": "base64","media_type": "image/jpeg"}
                source["data"] = model_kwargs['image']
                image_dic["source"] = source
                messages["content"].append(image_dic)

            if len(prompt) > 0:
                text_dic = {"type":"text"}
                text_dic["text"] = prompt
                messages['content'].append(text_dic)
            if 'related_docs' in model_kwargs.keys():
                docs = model_kwargs['related_docs']
                for doc in docs:
                    if 'text' in doc.keys():
                        doc_str = '相关文档信息为：'
                        if language == 'english':
                            doc_str = 'Related documentation information are:'
                        text_dic = {"type":"text"}
                        text_dic["text"] = doc_str + doc['text']
                        messages['content'].append(text_dic)
                    if 'image' in doc.keys() and len(doc['image']) > 0:
                        image_dic = {"type": "image"}
                        source = {"type": "base64","media_type": "image/jpeg"}
                        source["data"] = doc['image']
                        image_dic["source"] = source
                        messages['content'].append(image_dic)

            if 'history' in model_kwargs.keys():
                history_str = '历史记录为：'
                if language == 'english':
                    history_str = 'history records are:'
                text_dic = {"type":"text"}
                text_dic["text"] = history_str +  model_kwargs['history']
                messages['content'].append(text_dic)

            if 'input_docs' in model_kwargs.keys():
                docs = model_kwargs['input_docs']
                for doc in docs:
                    if 'text' in doc.keys():
                        doc_str = '用户输入为：'
                        if language == 'english':
                            doc_str = 'User input are:'
                        text_dic = {"type":"text"}
                        text_dic["text"] = doc_str + doc['text']
                        messages['content'].append(text_dic)
                    if 'image' in doc.keys():
                        image_dic = {"type": "image"}
                        source = {"type": "base64","media_type": "image/jpeg"}
                        source["data"] = doc['image']
                        image_dic["source"] = source
                        messages['content'].append(image_dic)

            input_body['messages'].append(messages)

        elif modelId == 'amazon.titan-tg1-large':
            input_body = {"inputText": prompt,
                                     "textGenerationConfig" : {
                                         "maxTokenCount": max_tokens,
                                         "stopSequences": [],
                                         "temperature":temperature,
                                         "topP":0.9
                                     }
                                     }
        elif modelId == 'amazon.titan-e1t-medium':
            input_body = {"inputText": prompt}
        elif modelId == 'meta.llama2-13b-chat-v1':
            input_body = {
                "prompt": prompt,
                "max_gen_len": max_tokens,
                "temperature": temperature,
                "top_p": 0.9
            }
        elif modelId.find('mistral') >=0:
            input_body = {
                "prompt": prompt,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "top_p": 0.9
            }
        else:
            input_body = {**model_kwargs}
            if provider == "anthropic":
                input_body["prompt"] = cls._human_assistant_format(prompt)
            elif provider == "ai21" or provider == "cohere":
                input_body["prompt"] = prompt
            elif provider == "amazon":
                input_body = dict()
                input_body["inputText"] = prompt
                input_body["textGenerationConfig"] = {**model_kwargs}
            else:
                input_body["prompt"] = prompt

            if provider == "anthropic" and "max_tokens_to_sample" not in input_body:
                input_body["max_tokens_to_sample"] = 256

            if "prompt" in input_body.keys():
                prompt = input_body['prompt']
        return input_body