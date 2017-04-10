#!/usr/bin/env python3
import json
from pprint import pprint


def main():

    try:
        with open("knowledge.txt") as f:
            knowledge = json.loads(f.read())
    except:
        right_answer = input("Think of something that I will have to guess: ")
        first_question = input("Enter a yes/no question where 'yes' would lead me to your guess: ")
        knowledge = {"question":first_question, "yes":right_answer}


    print("Think of something either from the list below (to check my intelligence) ")
    print("or something else to help me build my understanding.")
    print("\tKnown items:", ", ".join(extract_known_items(knowledge)))
    print("Ready?  Here we go...")

    prompt_knowledge_node(knowledge)
    pprint(knowledge)
    with open("knowledge.txt", "w") as f:
        f.write(json.dumps(knowledge,  indent=4))


def prompt_knowledge_node(knowledge):

    # Prompt user with the yes/no question
    branch_yn = input(knowledge["question"] + " (y/n): ").lower()

    if branch_yn in ("y", "yes"):
        branch_yn = "yes"
    elif branch_yn in ("q","quit"):
        print("Quitting")
        return knowledge
    else:
        branch_yn = "no"
    print(branch_yn)

    # Do we have a definitive guess now in the yes or no branch?
    if type(knowledge.get(branch_yn)) == str:

        # Else make final guess
        guess = knowledge.get(branch_yn)
        guessed_right_yn = input("Is it a {}? (y/n): ".format(guess)).lower()

        if guessed_right_yn in ("y", "yes"):
            guessed_right_yn = "yes"
        else:
            guessed_right_yn = "no"
        print(guessed_right_yn)

        # Got it right
        if guessed_right_yn == "yes":
            print("Got it!")
            return knowledge

        # Wrong: learn another question
        else:
            right_answer = input("What was the right answer? ")
            new_question = input("Enter a yes/no question that could differentiate between a {} and a {}: "
                                 .format(guess, right_answer))
            new_right_resp = input("Which response, yes or no, would point to the {}? ".format(right_answer)).lower()
            if new_right_resp in ("y", "yes"):
                resp_yes = right_answer
                resp_no = guess
            else:
                resp_yes = guess
                resp_no = right_answer
            node = {
                "question": new_question,
                "yes": resp_yes,
                "no": resp_no
            }
            knowledge[branch_yn] = node
            print("OK. Let's try it.")
            return prompt_knowledge_node(node)

    # Is it further questioning?
    elif type(knowledge.get(branch_yn)) == dict:
        return prompt_knowledge_node(knowledge.get(branch_yn))

    # Else, we give up
    elif branch_yn not in knowledge:
        right_answer = input("I give up.  What is it? ")
        new_question = input("Enter a yes/no question where 'yes' would lead me to your guess: ")
        node = {
            "question":new_question,
            "yes":right_answer
        }
        knowledge[branch_yn] = node
        print("OK. Let's try it.")
        return prompt_knowledge_node(node)


def extract_known_items(knowledge:dict)->[str]:
    items = []
    for yn in ("yes","no"):
        if yn in knowledge:
            if type(knowledge[yn]) == str:
                items.append(knowledge[yn])
            elif type(knowledge[yn]) == dict:
                items += extract_known_items(knowledge[yn])
    return items


if __name__ == "__main__":
    main()


