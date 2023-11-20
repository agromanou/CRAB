
import pandas as pd
import openai
import logging
import argparse
from pprint import pprint
import json
import time


def read_json(path):
    with open(path, "r") as f:
        data = json.load(f)
    return data

def ask_gpt_3(prompts,
            openai_key,
            test=True):
    """
    Asks gpt based on the given prompt and returns the predictions.
    """
    openai.api_key = openai_key

    predictions = list()
    if not test:
        # create a completion
        completion = openai.Completion.create(engine="text-davinci-003", 
                                              prompt=prompts,
                                              max_tokens=256,
                                              temperature=0.3)
        # store the completion
        for comp in completion.choices:
            response = comp.text
            predictions.append(response)
    
    return predictions


def ask_gpt_4(prompts, prompt_system, openai_key, test=True):
    
    openai.api_key = openai_key

    predictions = list()
    for prompt in prompts:
        messages=[{"role": "system", "content": prompt_system},
                  {"role": "user", "content": prompt}]

        # create a completion
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages = messages,
            temperature=0.2,
            max_tokens=256,
            frequency_penalty=0.0
        )
        predictions.append(response['choices'][0]['message']['content'])
    
    return predictions


def add_predictions(predictions, destination_file):
    to_store = predictions.to_dict(orient='records')
        
    with open(destination_file) as f:
        data = json.load(f)
        
    data.extend(to_store)
    
    with open(destination_file, "w") as f:
        json.dump(data, f , indent=4)

    print('NEW BATCH STORED!')

def set_prompt(x, selected_prompt):
    if x['0_choice'] == 'A':
        c_a = x['0_cause']
    elif x['0_choice'] == 'B':
        c_b = x['0_cause']
    elif x['0_choice'] == 'C':
        c_c = x['0_cause']
    else:
        c_d = x['0_cause']

    if x['1_choice'] == 'A':
        c_a = x['1_cause']
    elif x['1_choice'] == 'B':
        c_b = x['1_cause']
    elif x['1_choice'] == 'C':
        c_c = x['1_cause']
    else:
        c_d = x['1_cause']
    
    if x['2_choice'] == 'A':
        c_a = x['2_cause']
    elif x['2_choice'] == 'B':
        c_b = x['2_cause']
    elif x['2_choice'] == 'C':
        c_c = x['2_cause']
    else:
        c_d = x['2_cause']

    if x['3_choice'] == 'A':
        c_a = x['3_cause']
    elif x['3_choice'] == 'B':
        c_b = x['3_cause']
    elif x['3_choice'] == 'C':
        c_c = x['3_cause']
    else:
        c_d = x['3_cause']
            
    return selected_prompt.format(x['article_effect'], x['0_article'], x['1_article'],  x['2_article'],  x['3_article'], x['effect'], c_a, c_b, c_c, c_d)


def run_inference(dataset, 
                  prompt_name, 
                  prompt_system, 
                  destination_file,
                  openai_key,
                  model='gpt3'):
    
    results = pd.DataFrame()
    ranges_idx = list(range(20, len(dataset) + 20, 20))
    for range_idx in ranges_idx[122:]:        
        print('Running Inference for: {}-{} '.format(range_idx-20, range_idx))

        pair_sub = dataset[range_idx-20:range_idx].reset_index()

        prompts = list(pair_sub[prompt_name].values)
        
        should_break = False

        while not should_break:
            try:
                if model == 'gpt4':
                    predictions = ask_gpt_4(prompts=prompts, prompt_system=prompt_system, openai_key=openai_key, test=False)
                elif model == 'gpt3':
                    predictions = ask_gpt_3(prompts=prompts, prompt_system=prompt_system, openai_key=openai_key, test=False)

                else:
                    raise ValueError("Please provide a valid model name.")
                
                pair_sub['predictions_{}'.format(prompt_name)] = predictions
                print('Got results')

                results = pd.concat([results, pair_sub])
                should_break = True
            except Exception as e: 
                print('Error occured')
                print(e)
            
                time.sleep(5)
                pass

        if range_idx % 20==0:
            add_predictions(results, destination_file)
            results = pd.DataFrame()
        elif range_idx == 2740:
            print('Last predictions to be added')
            add_predictions(results, destination_file)


def main(openai_key, 
         dataset_path,
         prompt_name,
         destination_file,
         model):
    dataset = pd.read_json(dataset_path)
    prompts = read_json('prompts.json')

    print('Runing experiments for: {}'.format(prompt_name))
    print('Data will be stored in: {}'.format(destination_file))
    destination = pd.read_json(destination_file)
    print('Current size of destination json file: {}'.format(len(destination)))

    selected_prompt = None
    selected_prompt_system = None

    for prompt in prompts:
        if prompt['prompt_name']==prompt_name:
            selected_prompt = prompt['prompt_template']['question'] 
            selected_prompt_system = prompt['prompt_template']['instructions'] 

    if selected_prompt:

        dataset[prompt_name] = dataset.apply(lambda x: set_prompt(x, selected_prompt), axis=1)
        
        print(20*'-' + ' PROMPT ' + 50*'-')
        print(selected_prompt_system + selected_prompt)
        print(75*'-')
        
        print('Running Inference for {} samples'.format(len(dataset)))
        run_inference(dataset, prompt_name, selected_prompt_system, destination_file, openai_key, model)

    new_dataset = pd.read_json(destination_file)
    print('Data size of the predictions: {}'.format(len(new_dataset)))

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description='Ask GPT to generate graded causality predictions.')
    
    parser.add_argument('--model', 
                        required=False, 
                        default='gpt4',
                        help='')
    
    parser.add_argument('--openai-key', 
                        required=False, 
                        default='',
                        help='')
    
    parser.add_argument('--prompt-name', 
                        required=False, 
                        default='mcq_w_context',
                        help='')
    
    parser.add_argument('--data-path', 
                        required=False, 
                        default='data/graded_causality.jsonl',
                        help='')

    args = parser.parse_args()
    prompt_name = args.prompt_name
    
    destination_file = 'data/CRAB_graded_pred_{}_gpt4.json'.format(prompt_name)

    main(args.openai_key, 
         args.dataset_path,
         prompt_name,
         destination_file,
         args.model)

   
    

    