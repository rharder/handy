#!/usr/bin/env python3


def main():
    knowledge = {
        "question":"Is it smaller than a breadbox?",
        "yes": "rabbit"
    }
    k = prompt_knowledge_node(knowledge)
    print(k)


def prompt_knowledge_node(knowledge):

    # Prompt user for yes/no question
    branch_yn = input(knowledge["question"] + " (y/n): ")

    if branch_yn.lower in ("y", "yes"):
        branch_yn = "yes"
    else:
        branch_yn = "no"

    # If more questions to ask, dig deeper
    if isinstance(knowledge[branch_yn], dict):
        return prompt_knowledge_node(knowledge[branch_yn])

    # Else make final guess
    else:
        guess = knowledge[branch_yn]
        guessed_right_yn = input("Is it a(n) {}? (y/n): ".format(guess))

        if guessed_right_yn.lower in ("y", "yes"):
            guessed_right_yn = "yes"
        else:
            guessed_right_yn = "no"

        # Got it right
        if guessed_right_yn == "yes":
            print("Got it!")
            return knowledge

        # Wrong: learn another question
        else:
            right_answer = input("What was the right answer? ")
            new_question = input("Enter a yes/no question that could differentiate between a {} and a {}:"
                         .format(guess, right_answer))
            new_right_resp = input("Which response, yes or no, would point to the {}".format(right_answer))
            if new_right_resp.lower() in ("y", "yes"):
                resp_yes = right_answer
                resp_no = guess
            else:
                resp_yes = right_answer
                resp_no = guess
            node = {
                "question":new_question,
                "yes": resp_yes,
                "no": resp_no
            }
            knowledge[branch_yn] = node
            return prompt_knowledge_node(node)


if __name__ == "__main__":
    main()


