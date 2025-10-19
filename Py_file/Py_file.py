# -*- coding: utf-8 -*-
from fnmatch import translate
from fastapi import FastAPI,HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from language_tool_python import LanguageTool
from argostranslate  import translate,package
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from pycorrector.macbert.macbert_corrector import MacBertCorrector
import torch
import os
from langdetect import detect
import subprocess
import logging
from logging.handlers import RotatingFileHandler
import time

# uvicorn Py_file:app --host 0.0.0.0 --port 8000 --reload
# set TF_ENABLE_ONEDNN_OPTS=0
# java -cp "D:\visual\consoleapp1\tool\LanguageTool-6.1\languagetool-server.jar" org.languagetool.server.HTTPServer --port 8001 --allow-origin "*"


#配置日志记录 - 使用轮转文件处理器，每个文件最大1MB，保留3个备份
file_handler = RotatingFileHandler('app.log', encoding='utf-8', maxBytes=1024*1024, backupCount=3)
logging.basicConfig(
    handlers=[file_handler],
    format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level = logging.INFO
    )
logger = logging.getLogger("API")

app=FastAPI(title = "AI")

#允许跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins = ["*"],
    allow_methods = ["*"],
    allow_headers = ["*"]
    )

#语法检查模型
class Grammar(BaseModel):
    text: str
    language:str = "en-US"

#翻译模型
class Translation(BaseModel):
    text: str
    source_lang:str = "auto"
    target_lang:str = "en"

#润色模型
class  Polishing(BaseModel):
    text: str

#初始化工具缓存
_tools = {}

#获取语言工具
def get_language_tool(lang:str)->LanguageTool:
    if lang not in _tools:
        logger.info(f"初始化语言工具:{lang}")
        _tools[lang] = LanguageTool(lang,remote_server="http://localhost:8001")
    return _tools[lang]

def get_lt_lang(text, override=None):
    # 支持自定义，否则自动侦测
    if override:
        return override
    lang = detect(text)
    # Map langdetect结果到LanguageTool
    mapping = {
        "zh-CN": "zh",
        "zh": "zh",
        "en": "en-US",
        "fr": "fr",
        "ja-JP": "ja",
        # 可补充更多
    }
    return mapping.get(lang.lower(), "en-US")

#执行语法检查
@app.post("/api/grammar-check")
async def grammar_check(request:Grammar):
    try:
        tool_lang = request.language if request.language else get_lt_lang(request.text)
        tool = get_language_tool(tool_lang)
        matches = tool.check(request.text)
        print(f"matches: {matches}")
        return{
            "original":request.text,
            "issues":[{
                "start":match.offset,
                "end":match.offset + match.errorLength,
                "message":match.message,
                "replacements":match.replacements[:3]
            }for match in matches]
        }
    except Exception as e:
        logger.error(f"语法检查失败:{str(e)}")
        raise HTTPException(status_code=500,detail="语法检查服务异常")

#执行文本翻译
@app.post("/api/translate")
async def translate_text(request:Translation):
    try:
        # 自动检测源语言
        source_lang = detect(request.text) if request.source_lang == "auto" else request.source_lang
        source_lang = source_lang.split("-")[0]
        # 检查语言代码是否合法
        if source_lang not in ["zh", "en"]: 
            source_lang = "en"  # 默认回退到英文

        # 加载模型
        installed_languages = translate.get_installed_languages()
        if not installed_languages:
            raise HTTPException(status_code=500, detail="未找到翻译模型")
       
        # 匹配源语言和目标语言
        source_lang_obj = next((lang for lang in installed_languages if lang.code == source_lang), None)
        target_lang_obj = next((lang for lang in installed_languages if lang.code == request.target_lang), None)
        if not source_lang_obj or not target_lang_obj:
            raise HTTPException(status_code=500, detail="不支持的语言")

        translation = source_lang_obj.get_translation(target_lang_obj)
        translated_text = translation.translate(request.text)

        return {
            "original": request.text,
            "translated": translated_text,
            "source_lang": source_lang_obj.code,
            "target_lang": target_lang_obj.code
        }
    except Exception as e:
        logger.error(f"翻译失败:{str(e)}")
        raise HTTPException(status_code=500,detail=f"翻译服务异常:{str(e)}")

# 加载macbert4csc模型
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
corrector = MacBertCorrector(r"D:/visual/consoleapp1/tool/macbert4csc-base-chinese")

#执行语言润色
@app.post("/api/polish")
async def polish_text(request:Polishing):
    try:
        # 中文文本纠错
        polished = corrector.correct(request.text)
        return {
            "original": request.text,
            "polished": polished
        }
    except Exception as e:
        logger.error(f"语言润色失败:{str(e)}")
        raise HTTPException(status_code=500,detail="润色服务异常")

#启动LanguageTool服务器
def start_languagetool_server():
    try:
        # 指定LanguageTool本地路径
        lt_path = r"D:\visual\consoleapp1\tool\LanguageTool-6.1\languagetool-server.jar"
        # 使用subprocess启动
        subprocess.Popen(
            ["java", "-cp", lt_path,"org.languagetool.server.HTTPServer", "--port", "8001","--allow-origin", "*"],
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
            # 等待服务器启动
        time.sleep(5)
        logger.info("语法检查服务器已启动")
    except Exception as e:
        logger.error(f"启动语法检查服务器失败: {str(e)}")

# 加载翻译模型
def load_models():
    try:
        # 安装指定的翻译模型
        package.install_from_path( r"D:\visual\consoleapp1\tool\translate-zh_en-1_9.argosmodel")
        logger.info("翻译模型加载成功")
    except Exception as e:
        logger.error(f"翻译模型加载失败: {str(e)}")


@app.on_event("startup")
def startup_event():
    load_models()
    start_languagetool_server()

