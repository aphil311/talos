import argparse
import json
import os
import random
import re

from dotenv import load_dotenv
from openai import OpenAI
from tqdm import tqdm


def handle_args() -> tuple[argparse.Namespace, list, list]:
    """
    Handles command-line arguments.

    Returns:
        argparse.Namespace: Parsed arguments.
        constitution: List of dictionaries corresponding to the json file
        instructions: List of instructions to generate responses to
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "constitution", type=str, help="Path to the constitution JSON file"
    )
    parser.add_argument(
        "instructions", type=str, help="Path to the adversarial instructions"
    )
    parser.add_argument(
        "--batch_size",
        type=int,
        default=50,
        help="Number of instructions to process in a batch. This can help with performance.",
    )
    parser.add_argument(
        "--output_file",
        type=str,
        default="data.json",
        help="Output file to save the generated examples",
    )
    parser.add_argument("--debug", action="store_true")

    args = parser.parse_args()

    try:
        with open(args.constitution) as f:
            constitution = json.load(f)
    except Exception as e:
        print(f"Error reading constitution: {e}")
        exit(1)

    try:
        with open(args.instructions) as f:
            instructions = f.readlines()
    except Exception as e:
        print(f"Error reading instructions: {e}")
        exit(1)

    return args, constitution, instructions


def run_gpt_inference(system_prompt: str, prompt: str) -> str:
    """
    Generate crypto-themed questions from a given article text.

    Parameters:
        system_prompt: System prompt message
        prompt: Prompt to feed to the openai model

    Returns:
        str: Output from the openai model
    """
    # load api key from .env
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    client = OpenAI()
    client.api_key = api_key

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
        max_tokens=10_000,
    )

    raw_content = response.choices[0].message.content.strip()

    # strip quotes if needed
    if raw_content.startswith('"') and raw_content.endswith('"'):
        raw_content = raw_content[1:-1]
    return raw_content


def encode_prompt(instructions: list) -> str:
    """
    Encodes a list of instructions into a single string.

    Parameters:
        instructions: List of instructions to encode

    Returns:
        str: Encoded instructions
    """
    message = (
        "Below are a series of instructions. Please respond to each instruction "
        "with a numbered response that corresponds to the instruction number. Each response should be fairly short and conversational.\n\n"
    )

    numbered_instructions = "\n".join(
        [
            f"{i + 1}. {instruction.strip()}"
            for i, instruction in enumerate(instructions)
        ]
    )
    return message + numbered_instructions


def main():
    system_prompt_chat = (
        "You are a chatbot assistant tasked with responding to a user's message "
        "in a conversational manner. Your responses should be engaging and reasonably short (one line)."
    )
    system_prompt_help = (
        "You are a helpful AI assistant tasked with with generating a structured "
        "dataset for LLM finetuning based on a given set of rules."
    )
    args, constitution, instructions = handle_args()
    batch_size = args.batch_size

    if args.debug:
        debug_str = ""

    results = []
    for i in tqdm(range(0, len(instructions), batch_size)):
        prompt = encode_prompt(instructions[i : i + batch_size])
        naive = run_gpt_inference(system_prompt_chat, prompt)
        j = random.randint(0, len(constitution) - 1)

        critique_prompt = constitution[j].get("critique")
        revision_prompt = constitution[j].get("revision")

        # generate a critique prompt
        prompt = (
            f"The assistant responded to {str(instructions[i : i + batch_size])} with the following messages: {naive}.\n\n"
            + critique_prompt
            + "Please accomplish this task for each numbered response with a specific critique. Please number your critiques accordingly.\n\n"
        )

        # generate a critique response
        critique = run_gpt_inference(system_prompt_help, prompt)

        # generate a revision prompt
        prompt = (
            f"Given the critiques:\n{critique}\n\n"
            + revision_prompt
            + "Please number your final revised responses accordingly. Each response should be one line but may be several sentences.\n\n"
            + "Original messages: "
            + naive
        )

        # generate a revision response
        revision = run_gpt_inference(system_prompt_help, prompt)

        # Split the revision by newlines and strip numbering
        revision_lines = revision.strip().split("\n")
        revisions = []
        for line in revision_lines:
            line = line.strip()
            if not line:
                continue
            # Remove the numbering at the start of each entry
            stripped_line = re.sub(r"^\d+\.\s*", "", line)
            if stripped_line:  # Ignore empty lines
                revisions.append(stripped_line)

        # Split the naive response by newlines and strip numbering
        reject_lines = naive.strip().split("\n")
        rejects = []
        for line in reject_lines:
            line = line.strip()
            if not line:
                continue
            # Remove the numbering at the start of each entry
            stripped_line = re.sub(r"^\d+\.\s*", "", line)
            if stripped_line:  # Ignore empty lines
                rejects.append(stripped_line)
        
        # revisions = []
        # for i in range(1, batch_size+1):
        #     revision_text = ""
        #     start_pattern = f"{i}."
        #     end_pattern = f"{i + 1}."
        #     start_index = revision.find(start_pattern)
        #     end_index = revision.find(end_pattern, start_index + len(start_pattern))
        #     if start_index != -1:
        #         if end_index != -1:
        #             revision_text = revision[start_index + len(start_pattern):end_index]
        #         else:
        #             revision_text = revision[start_index + len(start_pattern):]
        #     else:
        #         # add to debug log and skip to next batch
        #         if args.debug:
        #             debug_str += f"=== DEBUG ENTRY: Revision text not found for instruction {i}\n"
        #             debug_str += f"Revision Text: {revision}\n"
        #             debug_str += f"Start Pattern: {start_pattern}\n"
        #             debug_str += f"End Pattern: {end_pattern}\n"
        #     if revision_text:
        #         # Clean the text by removing leading and trailing whitespace
        #         revision_text = revision_text.strip()
        #         # Add the cleaned text to the revisions list
        #         revisions.append(revision_text)

        # rejects = []
        # for i in range(1, batch_size+1):
        #     reject_text = ""
        #     start_pattern = f"{i}."
        #     end_pattern = f"{i + 1}."
        #     start_index = naive.find(start_pattern)
        #     end_index = naive.find(end_pattern, start_index + len(start_pattern))
        #     if start_index != -1:
        #         if end_index != -1:
        #             reject_text = naive[start_index + len(start_pattern):end_index]
        #         else:
        #             reject_text = naive[start_index + len(start_pattern):]
        #     else:
        #         # add to debug log and skip to next batch
        #         if args.debug:
        #             debug_str += f"=== DEBUG ENTRY: Reject text not found for instruction {i}\n"
        #             debug_str += f"Naive Text: {naive}\n"
        #             debug_str += f"Start Pattern: {start_pattern}\n"
        #             debug_str += f"End Pattern: {end_pattern}\n"
        #     if reject_text:
        #         # Clean the text by removing leading and trailing whitespace
        #         reject_text = reject_text.strip()
        #         # Add the cleaned text to the rejects list
        #         rejects.append(reject_text)
    
        # Ensure we have the same number of revisions and naives
        if len(rejects) < len(revisions):
            rejects.extend([""] * (len(revisions) - len(rejects)))
        elif len(rejects) > len(revisions):
            revisions.extend([""] * (len(rejects) - len(rejects)))


        for k in range(batch_size):
            instruction = instructions[i + k].rstrip("\n")
            results.append(
                {
                    "prompt": instruction,
                    "chosen": revisions[k],
                    "rejected": rejects[k],
                }
            )

        if args.debug:
            s = (
                f"=== DEBUG ENTRY ============================================\n"
                f"Prompt:\n{instructions[i]}\n------------------------------\n"
                f"Naive Response:\n{naive}\n------------------------------\n"
                f"Critique Prompt:\n{critique_prompt}\n------------------------------\n"
                f"Critique:\n{critique}\n------------------------------\n"
                f"Revision Prompt:\n{revision_prompt}\n------------------------------\n"
                f"Revision:\n{revision}\n------------------------------\n"
            )
            debug_str += s

    # save the results to a json
    with open(args.output_file, "w") as f:
        json.dump(results, f, indent=4)
    print(f"Results saved to {args.output_file}")

    if args.debug:
        with open("debug.log", "w") as f:
            f.write(debug_str)
        print("Debug information saved to debug.log")


if __name__ == "__main__":
    main()
