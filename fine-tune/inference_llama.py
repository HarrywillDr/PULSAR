import json
import fire
import torch
from transformers import GenerationConfig, AutoModelForSeq2SeqLM, AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel
import pandas as pd
from tqdm import tqdm

def load_model(model_path, adapter_path=None, is_causal=True, load_in_8bit=False):
    AutoModelClass = AutoModelForCausalLM if is_causal else AutoModelForSeq2SeqLM
    print(f"Loading {AutoModelClass.__name__} from {model_path}.")
    
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model = AutoModelClass.from_pretrained(
        model_path, load_in_8bit=load_in_8bit, torch_dtype=torch.float16, device_map="auto"
    )

    if adapter_path:
        print(f"Loading adapter weights from {adapter_path}.")        
        model = PeftModel.from_pretrained(
                model,
                adapter_path,
                torch_dtype=torch.float16,
            ).float().eval()
        
    return tokenizer, model

def test(tokenizer, model, prompt, temperature=0.1, top_p=0.7, top_k=40, num_beams=4, max_new_tokens=160, **kwargs):
    input_ids = tokenizer(prompt, return_tensors="pt").input_ids
    generation_config = GenerationConfig(
        temperature=temperature, top_p=top_p, top_k=top_k, num_beams=num_beams, **kwargs
    )
    generation_output = model.generate(
        input_ids=input_ids.cuda(),
        generation_config=generation_config,
        return_dict_in_generate=True,
        output_scores=True,
        max_new_tokens=max_new_tokens,
    )

    return tokenizer.batch_decode(generation_output.sequences, skip_special_tokens=True)[0]

def infer(
    base_model: str = "",
    adapter_path: str = None,
    test_dataset: str = None,
    temperature: float = 0.1,
    preds_out: str = 'system.txt',
    top_p: float = 0.7,
    top_k: int = 40,
    num_beams: int = 4,
    max_new_tokens: int = 160,
    load_in_8bit: bool = True,
    is_causal: bool = True
):
    tokenizer, model = load_model(base_model, adapter_path, is_causal=is_causal, load_in_8bit=load_in_8bit)
    ds = pd.read_csv(test_dataset).to_dict(orient='records')
    results = []
    for example in tqdm(ds):
        prompt = f"{input}\n Medical note:"
        output = test(tokenizer, model, prompt, temperature, top_p, top_k, num_beams, max_new_tokens)
        prediction = output.split('Medical note:', 1)[-1]
        print(prompt, prediction)
        results.append(prediction)
    with open('system.txt') as f:
        f.write('\n'.join(json.dumps(r) for r in results))

if __name__ == "__main__":
    fire.Fire(infer)