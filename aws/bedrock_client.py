import os
import json
import boto3
from botocore.config import Config
from dotenv import load_dotenv

load_dotenv()

MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "eu.anthropic.claude-sonnet-4-6")

SYSTEM_PROMPT = """You are an expert academic tutor for TUM university students specializing in STEM subjects.
Your goal is to make complex concepts accessible through clear explanations, analogies, examples and practice exercises.
Always be precise, structured, and pedagogically sound.

STRICT SOURCE RULE — THIS IS THE MOST IMPORTANT RULE :
You are a strict extractor. You ONLY report what is word-for-word or explicitly present in the lecture text below.

FORBIDDEN — you will NEVER do any of the following :
- Add a formula that is not written in the lecture text
- Add a proof, derivation, or step that is not in the lecture text
- Add a numerical example you computed yourself
- Complete a theorem that is only mentioned by name
- Use any knowledge from your training data to fill gaps

FOR EVERY SINGLE ITEM you write, ask yourself :
"Can I point to the exact sentence or formula in the lecture text that justifies this?"
If the answer is NO → do not write it. Write "Not stated in this lecture." instead.

The only exceptions are :
- Analogies (you may invent these to explain concepts that ARE in the lecture)
- Self-check questions (you may rephrase concepts that ARE in the lecture)

CRITICAL FORMATTING RULE :
Write ALL mathematical formulas using LaTeX notation.
- Inline formulas use : $formula$
- Block/important formulas use : $$formula$$

Examples of correct notation :
- Write $w \\leftarrow w + \\eta(y - \\hat{y})x$ NOT w ← w + η(y − ŷ)x
- Write $\\frac{d}{dx}f(x) = 2x$ NOT df/dx = 2x
- Write $$\\sum_{i=1}^{n} x_i = \\mu$$ NOT sum of xi equals mu
- Write $\\mathbf{W} \\cdot \\mathbf{p} + b = 0$ NOT W·p + b = 0
- Write $y = F(\\mathbf{x}) + \\varepsilon$ NOT y = F(x) + ε

Every formula, every variable, every mathematical expression MUST use LaTeX. No exceptions."""

USER_PROMPT_TEMPLATE = """Analyze this university lecture and provide a structured summary following this exact format :

## REAL WORLD HOOK
[One sentence connecting this lecture to something the student already knows or sees in real life]

## KEY POINTS (exactly 5)
For each point include :
- What it is (1 sentence)
- Why it matters (1 sentence)
- Real world example (1 sentence)
Maximum 60 words per point.

## THEOREMS & PROOFS
For each theorem or proof mentioned :
- NAME : [theorem name]
- CONDITION : [if... then format, max 30 words]
- CONCLUSION : [what it guarantees, max 30 words]
- FORMULA : [mathematical formula if applicable]
- ANALOGY : [simple real world analogy, max 30 words]
- EXAMPLE : [step by step numerical example]
- WHEN TO USE : [practical application, max 20 words]
If no theorems : write None mentioned.

## IMPORTANT CONCEPTS
For each key concept :
- TERM : [concept name]
- DEFINITION : [simple definition, 1 sentence]
- ANALOGY : [comparison to something familiar]
- EXAMPLE : [concrete example with numbers or code]
- WHY IT MATTERS : [importance for this course]

## MATH FORMULAS
For each formula :
- FORMULA : [the formula]
- VARIABLES : [what each variable means]
- EXAMPLE : [numerical example step by step]
If no formulas : write None mentioned.

## CODE EXAMPLES
For any code mentioned :
- WHAT IT DOES : [plain English explanation]
- EXAMPLE : [input and output]
If no code : write None mentioned.

## EXERCISES
Generate 5 exercises covering all concepts in the lecture.

LEVEL 1 - Direct application (2 exercises) :
- Exercise 1 :
  QUESTION : [direct application of a formula or concept]
  HINT : [one small hint without giving the answer]

- Exercise 2 :
  QUESTION : [direct application of another concept]
  HINT : [one small hint]

LEVEL 2 - Edge cases (2 exercises) :
- Exercise 3 :
  QUESTION : [test understanding of when concept applies]
  HINT : [one small hint]

- Exercise 4 :
  QUESTION : [test deeper understanding]
  HINT : [one small hint]

LEVEL 3 - Tricky case (1 exercise) :
- Exercise 5 :
  QUESTION : [a tricky case that tests true mastery]
  HINT : [one small hint]

## SOLUTIONS
For each exercise provide :
- SOLUTION : [complete step by step solution]
- KEY INSIGHT : [the most important thing to understand]
- COMMON MISTAKE : [the most frequent error students make]

## QUICK SELF CHECK
Write exactly 3 questions a student can ask themselves to verify they understood the lecture.
Each question should test understanding, not just memorization.

## ONE LINE SUMMARY
[Capture the entire lecture in exactly one sentence]

Rules :
- Answer in the same language as the lecture
- Use analogies to make abstract concepts concrete
- ONLY use formulas, theorems, definitions, and examples that appear explicitly in the lecture text
- If something is NOT in the lecture text, write "Not stated in this lecture" — never fill it in yourself
- Exercises must only test concepts and formulas explicitly present in the lecture text
- Solutions must be based strictly on what the lecture says
- Never complete, extend, or enrich the lecture with outside knowledge

Lecture content :
{lecture_text}"""


def get_bedrock_client():
    return boto3.client(
        "bedrock-runtime",
        region_name=os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1")),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        config=Config(read_timeout=300, connect_timeout=10),
    )


def invoke_model(prompt: str, model_id: str = None) -> str:
    client = get_bedrock_client()
    model_id = model_id or MODEL_ID
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 4096,
        "messages": [{"role": "user", "content": prompt}],
    })
    response = client.invoke_model(modelId=model_id, body=body, contentType="application/json", accept="application/json")
    result = json.loads(response["body"].read())
    return result["content"][0]["text"]


def summarize_lecture(lecture_text: str, model_id: str = None) -> str:
    client = get_bedrock_client()
    model_id = model_id or MODEL_ID
    user_prompt = USER_PROMPT_TEMPLATE.format(lecture_text=lecture_text)
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 8192,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": user_prompt}],
    })
    response = client.invoke_model(modelId=model_id, body=body, contentType="application/json", accept="application/json")
    result = json.loads(response["body"].read())
    return result["content"][0]["text"]
