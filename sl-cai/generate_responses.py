import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from tqdm import tqdm

def run_llama_inference(prompt: str, model):
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    
    with torch.no_grad():
        output = model.generate(**inputs, max_new_tokens=100)
    
    response = tokenizer.decode(output[0], skip_special_tokens=True)
    return response

def load_model():
    model_name = "meta-llama/Llama-3.2-3B-Instruct"
    
    print("Loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    
    print("Loading model...")
    model = AutoModelForCausalLM.from_pretrained(model_name, device_map="auto")

    return model, tokenizer

if __name__ == "__main__":
    model, tokenizer = load_model()
    if model is not None and tokenizer is not None:
        print("Model loaded successfully! Running inference...")
    
    # powerloop
    for i in tqdm(range(512)):
        prompt = ''
        response = run_llama_inference(prompt, model)
        print(response)
    # read prompts from a file and run inference
    
    # tell model to critique

    # generate better response
