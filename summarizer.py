from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
from langdetect import detect
import textwrap
import torch
import functools
from transformers import PegasusTokenizer


def summarize(article):
    text=article
    language = detect(text)

    model,tokenizer= load_resources(language)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)

    inputs = tokenizer.encode(text, return_tensors="pt", max_length=1024, truncation=True)
    inputs = inputs.to(device)

    summary_ids = model.generate(inputs, max_length=150, min_length=50, length_penalty=2.0, num_beams=4, early_stopping=True)

    summary_ids = summary_ids.to(device)

    summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)
    summary=format(summary)
    return summary



@functools.lru_cache(maxsize=2)
def load_resources(language):
    if language=="ar":
        saved_model_dir = "./arabic"
        tokenizer = AutoTokenizer.from_pretrained(saved_model_dir, local_files_only=True)

    elif language=="en":
        saved_model_dir = "./english"
        tokenizer = PegasusTokenizer.from_pretrained(saved_model_dir, local_files_only=True)
    else:
        return "not suported lang"
    model = AutoModelForSeq2SeqLM.from_pretrained(saved_model_dir, local_files_only=True)
    return model,tokenizer





def format(summary):
    formatted_summary = "\n".join(textwrap.wrap(summary, width=80))
    return formatted_summary

