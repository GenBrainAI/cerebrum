You are python top level engineer working of a project that aims to develop an agentic framework that know how to solve problems of certain types using the development of agentic framework, like CrewAI, AutoGen, phidata, llama index, lang graph an others.



Text Completions

# Create a Text Completion

\[Legacy\] Create a Text Completion.

The Text Completions API is a legacy API. We recommend using the [Messages API](https://docs.anthropic.com/en/api/messages) going forward.

Future models and features will not be compatible with Text Completions. See our [migration guide](https://docs.anthropic.com/en/api/migrating-from-text-completions-to-messages) for guidance in migrating from Text Completions to Messages.

POST

/

v1

/

complete

cURL

Copy

```
curl https://api.anthropic.com/v1/complete \
     --header "x-api-key: $ANTHROPIC_API_KEY" \
     --header "anthropic-version: 2023-06-01" \
     --header "content-type: application/json" \
     --data \
'{
    "model": "claude-2.1",
    "max_tokens_to_sample": 1024,
    "prompt": "\n\nHuman: Hello, Claude\n\nAssistant:"
}'
```

200

4XX

Copy

```
{
  "completion": " Hello! My name is Claude.",
  "id": "compl_018CKm6gsux7P8yMcwZbeCPw",
  "model": "claude-2.1",
  "stop_reason": "stop_sequence",
  "type": "completion"
}
```

#### Body

application/json

model

string

required

The model that will complete your prompt.

See [models](https://docs.anthropic.com/en/docs/models-overview) for additional details and options.

prompt

string

required

The prompt that you want Claude to complete.

For proper response generation you will need to format your prompt using alternating `\n\nHuman:` and `\n\nAssistant:` conversational turns. For example:

```
"\n\nHuman: {userQuestion}\n\nAssistant:"
```

See [prompt validation](https://docs.anthropic.com/en/api/prompt-validation) and our guide to [prompt design](https://docs.anthropic.com/en/docs/intro-to-prompting) for more details.

max\_tokens\_to\_sample

integer

required

The maximum number of tokens to generate before stopping.

Note that our models may stop _before_ reaching this maximum. This parameter only specifies the absolute maximum number of tokens to generate.

stop\_sequences

string\[\]

Sequences that will cause the model to stop generating.

Our models stop on `"\n\nHuman:"`, and may include additional built-in stop sequences in the future. By providing the stop\_sequences parameter, you may include additional strings that will cause the model to stop generating.

temperature

number

Amount of randomness injected into the response.

Defaults to `1.0`. Ranges from `0.0` to `1.0`. Use `temperature` closer to `0.0` for analytical / multiple choice, and closer to `1.0` for creative and generative tasks.

Note that even with `temperature` of `0.0`, the results will not be fully deterministic.

top\_p

number

Use nucleus sampling.

In nucleus sampling, we compute the cumulative distribution over all the options for each subsequent token in decreasing probability order and cut it off once it reaches a particular probability specified by `top_p`. You should either alter `temperature` or `top_p`, but not both.

Recommended for advanced use cases only. You usually only need to use `temperature`.

top\_k

integer

Only sample from the top K options for each subsequent token.

Used to remove "long tail" low probability responses. [Learn more technical details here](https://towardsdatascience.com/how-to-sample-from-language-models-682bceb97277).

Recommended for advanced use cases only. You usually only need to use `temperature`.

metadata

object

An object describing metadata about the request.

Show child attributes

metadata.user\_id

string | null

An external identifier for the user who is associated with the request.

This should be a uuid, hash value, or other opaque identifier. Anthropic may use this id to help detect abuse. Do not include any identifying information such as name, email address, or phone number.

stream

boolean

Whether to incrementally stream the response using server-sent events.

See [streaming](https://docs.anthropic.com/en/api/streaming) for details.

#### Response

200 - application/json

type

enum<string>

default: completionrequired

Object type.

For Text Completions, this is always `"completion"`.

Available options:

`completion`

id

string

required

Unique object identifier.

The format and length of IDs may change over time.

completion

string

required

The resulting completion up to and excluding the stop sequences.

stop\_reason

string | null

required

The reason that we stopped.

This may be one the following values:

- `"stop_sequence"`: we reached a stop sequence — either provided by you via the `stop_sequences` parameter, or a stop sequence built into the model
- `"max_tokens"`: we exceeded `max_tokens_to_sample` or the model's maximum

model

string

required

The model that handled the request.


Client SDKs
We provide libraries in Python and Typescript that make it easier to work with the Anthropic API.

Additional configuration is needed to use Anthropic’s Client SDKs through a partner platform. If you are using Amazon Bedrock, see this guide; if you are using Google Cloud Vertex AI, see this guide.

​
Python
Python library GitHub repo

Example:

Python

import anthropic

client = anthropic.Anthropic(
    # defaults to os.environ.get("ANTHROPIC_API_KEY")
    api_key="my_api_key",
)
message = client.messages.create(
    model="claude-3-5-sonnet-20240620",
    max_tokens=1024,
    messages=[
        {"role": "user", "content": "Hello, Claude"}
    ]
)
print(message.content)
​
Typescript
Typescript library GitHub repo

Example:

Typescript

import Anthropic from '@anthropic-ai/sdk';

const anthropic = new Anthropic({
  apiKey: 'my_api_key', // defaults to process.env["ANTHROPIC_API_KEY"]
});

const msg = await anthropic.messages.create({
  model: "claude-3-5-sonnet-20240620",
  max_tokens: 1024,
  messages: [{ role: "user", content: "Hello, Claude" }],
});
console.log(msg);


Define your success criteria
Building a successful LLM-based application starts with clearly defining your success criteria. How will you know when your application is good enough to publish?

Having clear success criteria ensures that your prompt engineering & optimization efforts are focused on achieving specific, measurable goals.

​
Building strong criteria
Good success criteria are:

Specific: Clearly define what you want to achieve. Instead of “good performance,” specify “accurate sentiment classification.”

Measurable: Use quantitative metrics or well-defined qualitative scales. Numbers provide clarity and scalability, but qualitative measures can be valuable if consistently applied along with quantitative measures.

Even “hazy” topics such as ethics and safety can be quantified:
Safety criteria
Bad	Safe outputs
Good	Less than 0.1% of outputs out of 10,000 trials flagged for toxicity by our content filter.

Example metrics and measurement methods

Achievable: Base your targets on industry benchmarks, prior experiments, AI research, or expert knowledge. Your success metrics should not be unrealistic to current frontier model capabilities.

Relevant: Align your criteria with your application’s purpose and user needs. Strong citation accuracy might be critical for medical apps but less so for casual chatbots.


Example task fidelity criteria for sentiment analysis

​
Common success criteria to consider
Here are some criteria that might be important for your use case. This list is non-exhaustive.


Task fidelity


Consistency


Relevance and coherence


Tone and style


Privacy preservation


Context utilization


Latency


Price

Most use cases will need multidimensional evaluation along several success criteria.


Example multidimensional criteria for sentiment analysis

Criteria
Bad	The model should classify sentiments well
Good	On a held-out test set of 10,000 diverse Twitter posts, our sentiment analysis model should achieve:
- an F1 score of at least 0.85
- 99.5% of outputs are non-toxic
- 90% of errors are would cause inconvenience, not egregious error*
- 95% response time < 200ms
*In reality, we would also define what “inconvenience” and “egregious” means.


BUILD WITH CLAUDE
Create strong empirical evaluations
After defining your success criteria, the next step is designing evaluations to measure LLM performance against those criteria. This is a vital part of the prompt engineering cycle.



This guide focuses on how to develop your test cases.

​
Building evals and test cases
​
Eval design principles
Be task-specific: Design evals that mirror your real-world task distribution. Don’t forget to factor in edge cases!

Example edge cases

Automate when possible: Structure questions to allow for automated grading (e.g., multiple-choice, string match, code-graded, LLM-graded).
Prioritize volume over quality: More questions with slightly lower signal automated grading is better than fewer questions with high-quality human hand-graded evals.
​
Example evals

Task fidelity (sentiment analysis) - exact match evaluation


Consistency (FAQ bot) - cosine similarity evaluation


Relevance and coherence (summarization) - ROUGE-L evaluation


Tone and style (customer service) - LLM-based Likert scale


Privacy preservation (medical chatbot) - LLM-based binary classification


Context utilization (conversation assistant) - LLM-based ordinal scale

Writing hundreds of test cases can be hard to do by hand! Get Claude to help you generate more from a baseline set of example test cases.
If you don’t know what eval methods might be useful to assess for your success criteria, you can also brainstorm with Claude!
​
Grading evals
When deciding which method to use to grade evals, choose the fastest, most reliable, most scalable method:

Code-based grading: Fastest and most reliable, extremely scalable, but also lacks nuance for more complex judgements that require less rule-based rigidity.

Exact match: output == golden_answer
String match: key_phrase in output
Human grading: Most flexible and high quality, but slow and expensive. Avoid if possible.

LLM-based grading: Fast and flexible, scalable and suitable for complex judgement. Test to ensure reliability first then scale.

​
Tips for LLM-based grading
Have detailed, clear rubrics: “The answer should always mention ‘Acme Inc.’ in the first sentence. If it does not, the answer is automatically graded as ‘incorrect.‘”
A given use case, or even a specific success criteria for that use case, might require several rubrics for holistic evaluation.
Empirical or specific: For example, instruct the LLM to output only ‘correct’ or ‘incorrect’, or to judge from a scale of 1-5. Purely qualitative evaluations are hard to assess quickly and at scale.
Encourage reasoning: Ask the LLM to think first before deciding an evaluation score, and then discard the reasoning. This increases evaluation performance, particularly for tasks requiring complex judgement.

Example: LLM-based grading


import anthropic

def build_grader_prompt(answer, rubric):
    return f"""Grade this answer based on the rubric:
    <rubric>{rubric}</rubric>
    <answer>{answer}</answer>
    Think through your reasoning in <thinking> tags, then output 'correct' or 'incorrect' in <result> tags.""

def grade_completion(output, golden_answer):
    grader_response = client.messages.create(
        model="claude-3-opus-20240229",
        max_tokens=2048,
        messages=[{"role": "user", "content": build_grader_prompt(output, golden_answer)}]
    ).content[0].text

    return "correct" if "correct" in grader_response.lower() else "incorrect"

# Example usage
eval_data = [
    {"question": "Is 42 the answer to life, the universe, and everything?", "golden_answer": "Yes, according to 'The Hitchhiker's Guide to the Galaxy'."},
    {"question": "What is the capital of France?", "golden_answer": "The capital of France is Paris."}
]

def get_completion(prompt: str):
    message = client.messages.create(
        model="claude-3-5-sonnet-20240620",
        max_tokens=1024,
        messages=[
        {"role": "user", "content": prompt}
        ]
    )
    return message.content[0].text

outputs = [get_completion(q["question"]) for q in eval_data]
grades = [grade_completion(output, a["golden_answer"]) for output, a in zip(outputs, eval_data)]
print(f"Score: {grades.count('correct') / len(grades) * 100}%")

Build with Claude

# Embeddings

Text embeddings are numerical representations of text that enable measuring semantic similarity. This guide introduces embeddings, their applications, and how to use embedding models for tasks like search, recommendations, and anomaly detection.

## 

[​

](https://docs.anthropic.com/en/docs/build-with-claude/embeddings#before-implementing-embeddings)

Before implementing embeddings

When selecting an embeddings provider, there are several factors you can consider depending on your needs and preferences:

- **Dataset size & domain specificity:** size of the model training dataset and its relevance to the domain you want to embed. Larger or more domain-specific data generally produces better in-domain embeddings
- **Inference performance:** embedding lookup speed and end-to-end latency. This is a particularly important consideration for large scale production deployments
- **Customization:** options for continued training on private data, or specialization of models for very specific domains. This can improve performance on unique vocabularies

---

## 

[​

](https://docs.anthropic.com/en/docs/build-with-claude/embeddings#how-to-get-embeddings-with-anthropic)

How to get embeddings with Anthropic

Anthropic does not offer its own embedding model. One embeddings provider that has a wide variety of options and capabilities encompassing all of the above considerations is [Voyage AI](https://www.voyageai.com/?ref=anthropic).

Voyage AI makes [state-of-the-art](https://blog.voyageai.com/2023/10/29/voyage-embeddings/?ref=anthropic) embedding models and offers customized models for specific industry domains such as finance and healthcare, or bespoke fine-tuned models for individual customers.

The rest of this guide is for Voyage AI, but we encourage you to assess a variety of embeddings vendors to find the best fit for your specific use case.

---

## 

[​

](https://docs.anthropic.com/en/docs/build-with-claude/embeddings#getting-started-with-voyage-ai)

Getting started with Voyage AI

Check out our [embeddings notebook](https://github.com/anthropics/anthropic-cookbook/blob/main/third%5Fparty/VoyageAI/how%5Fto%5Fcreate%5Fembeddings.md) to see an example Voyage AI implementation.

To access Voyage embeddings:

1. Sign up on [Voyage AI’s website](https://dash.voyageai.com/?ref=anthropic)
2. Obtain an API key
3. Set the API key as an environment variable for convenience:

Python

Copy

```Python
export VOYAGE_API_KEY="<your secret key>"
```

You can run the embeddings by either using the official [voyageai Python package](https://github.com/voyage-ai/voyageai-python) or HTTP requests, as described below.

### 

[​

](https://docs.anthropic.com/en/docs/build-with-claude/embeddings#voyage-python-package)

Voyage Python package

The `voyageai` package can be installed using the following command:

Python

Copy

```Python
pip install -U voyageai
```

Then, you can create a client object and start using it to embed your texts:

Python

Copy

```Python
import voyageai

vo = voyageai.Client()
# This will automatically use the environment variable VOYAGE_API_KEY.
# Alternatively, you can use vo = voyageai.Client(api_key="<your secret key>")

texts = ["Sample text 1", "Sample text 2"]

result = vo.embed(texts, model="voyage-2", input_type="document")
print(result.embeddings[0])
print(result.embeddings[1])
```

`result.embeddings` will be a list of two embedding vectors, each containing 1024 floating-point numbers.

After running the above code, the two embeddings will be printed on the screen:

Python

Copy

```Python
[0.02012746, 0.01957859, ...]  # embedding for "Sample text 1"
[0.01429677, 0.03077182, ...]  # embedding for "Sample text 2"
```

When creating the embeddings, you may specify a few other arguments to the `embed()` function. Here is the specification:

> `voyageai.Client.embed(texts : List[str], model : str, input_type : Optional[str] = None, truncation : Optional[bool] = None)`

- **texts** (List\[str\]) - A list of texts as a list of strings, such as `["I like cats", "I also like dogs"]`. Currently, the maximum length of the list is 128, and total number of tokens in the list is at most 320K for `voyage-2` and 120K for `voyage-large-2`/`voyage-code-2`.
- **model** (str) - Name of the model. Recommended options: `voyage-2`, `voyage-large-2`, `voyage-code-2`.
- **input\_type** (str, optional, defaults to `None`) - Type of the input text. Defaults to `None`. Other options: `query`, `document`
    - When the input\_type is set to `None`, the input text will be directly encoded by Voyage’s embedding model. Alternatively, when the inputs are documents or queries, the users can specify `input_type` to be `query` or `document`, respectively. In such cases, Voyage will prepend a special prompt to input text and send the extended inputs to the embedding model
    - For retrieval/search use cases, we recommend specifying this argument when encoding queries or documents to enhance retrieval quality. Embeddings generated with and without the `input_type` argument are compatible
- **truncation** (bool, optional, defaults to `None`) - Whether to truncate the input texts to fit within the context length.
    - If `True`, over-length input texts will be truncated to fit within the context length, before being vectorized by the embedding model
    - If `False`, an error will be raised if any given text exceeds the context length
    - If not specified (defaults to `None`), Voyage will truncate the input text before sending it to the embedding model if it slightly exceeds the context window length. If it significantly exceeds the context window length, an error will be raised

### 

[​

](https://docs.anthropic.com/en/docs/build-with-claude/embeddings#voyage-http-api)

Voyage HTTP API

You can also get embeddings by requesting the Voyage HTTP API. For example, you can send an HTTP request through the `curl` command in a terminal:

Shell

Copy

```bash
curl https://api.voyageai.com/v1/embeddings \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $VOYAGE_API_KEY" \
  -d '{
    "input": ["Sample text 1", "Sample text 2"],
    "model": "voyage-2"
  }'
```

The response you would get is a JSON object containing the embeddings and the token usage:

Shell

Copy

```json
{
  "object": "list",
  "data": [
    {
      "embedding": [0.02012746, 0.01957859, ...],
      "index": 0
    },
    {
      "embedding": [0.01429677, 0.03077182, ...],
      "index": 1
    }
  ],
  "model": "voyage-2",
  "usage": {
    "total_tokens": 10
  }
}
```

Voyage AI’s embedding endpoint is `https://api.voyageai.com/v1/embeddings` (POST). The request header must contain the API key. The request body is a JSON object containing the following arguments:

- **input** (str, List\[str\]) - A single text string, or a list of texts as a list of strings. Currently, the maximum length of the list is 128, and total number of tokens in the list is at most 320K for `voyage-2` and 120K for `voyage-large-2`/`voyage-code-2`.
- **model** (str) - Name of the model. Recommended options: `voyage-2`, `voyage-large-2`, `voyage-code-2`.
- **input\_type** (str, optional, defaults to `None`) - Type of the input text. Defaults to `None`. Other options: `query`, `document`
- **truncation** (bool, optional, defaults to `None`) - Whether to truncate the input texts to fit within the context length
    - If `True`, over-length input texts will be truncated to fit within the context length before being vectorized by the embedding model
    - If `False`, an error will be raised if any given text exceeds the context length
    - If not specified (defaults to `None`), Voyage will truncate the input text before sending it to the embedding model if it slightly exceeds the context window length. If it significantly exceeds the context window length, an error will be raised
- **encoding\_format** (str, optional, default to `None`) - Format in which the embeddings are encoded. Voyage currently supports two options:
    - If not specified (defaults to `None`): the embeddings are represented as lists of floating-point numbers
    - `"base64"`: the embeddings are compressed to [Base64](https://docs.python.org/3/library/base64.html) encodings

---

## 

[​

](https://docs.anthropic.com/en/docs/build-with-claude/embeddings#voyage-embedding-example)

Voyage embedding example

Now that we know how to get embeddings with Voyage, let’s see it in action with a brief example.

Suppose we have a small corpus of six documents to retrieve from

Python

Copy

```Python
documents = [
    "The Mediterranean diet emphasizes fish, olive oil, and vegetables, believed to reduce chronic diseases.",
    "Photosynthesis in plants converts light energy into glucose and produces essential oxygen.",
    "20th-century innovations, from radios to smartphones, centered on electronic advancements.",
    "Rivers provide water, irrigation, and habitat for aquatic species, vital for ecosystems.",
    "Apple’s conference call to discuss fourth fiscal quarter results and business updates is scheduled for Thursday, November 2, 2023 at 2:00 p.m. PT / 5:00 p.m. ET.",
    "Shakespeare's works, like 'Hamlet' and 'A Midsummer Night's Dream,' endure in literature."
]
```

We will first use Voyage to convert each of them into an embedding vector

Python

Copy

```Python
import voyageai

vo = voyageai.Client()

# Embed the documents
doc_embds = vo.embed(
    documents, model="voyage-2", input_type="document"
).embeddings
```

The embeddings will allow us to do semantic search / retrieval in the vector space. We can then convert an example query,

Python

Copy

```Python
query = "When is Apple's conference call scheduled?"
```

into an embedding, and then conduct a nearest neighbor search to find the most relevant document based on the distance in the embedding space.

Python

Copy

```Python
import numpy as np

# Embed the query
query_embd = vo.embed(
    [query], model="voyage-2", input_type="query"
).embeddings[0]

# Compute the similarity
# Voyage embeddings are normalized to length 1, therefore dot-product
# and cosine similarity are the same.
similarities = np.dot(doc_embds, query_embd)

retrieved_id = np.argmax(similarities)
print(documents[retrieved_id])
```

Note that we use `input_type="document"` and `input_type="query"` for embedding the document and query, respectively. More specification can be found [here](https://docs.anthropic.com/en/docs/build-with-claude/embeddings#voyage-python-package).

The output would be the 5th document, which is indeed the most relevant to the query:

Copy

```
Apple’s conference call to discuss fourth fiscal quarter results and business updates is scheduled for Thursday, November 2, 2023 at 2:00 p.m. PT / 5:00 p.m. ET.
```

---

## 

[​

](https://docs.anthropic.com/en/docs/build-with-claude/embeddings#available-voyage-models)

Available Voyage models

Voyage recommends using the following embedding models:

| Model | Context Length | Embedding Dimension | Description |
| --- | --- | --- | --- |
| `voyage-large-2` | 16000 | 1536 | Voyage AI’s most powerful generalist embedding model. |
| `voyage-code-2` | 16000 | 1536 | Optimized for code retrieval (17% better than alternatives), and also SoTA on general-purpose corpora. See this Voyage [blog post](https://blog.voyageai.com/2024/01/23/voyage-code-2-elevate-your-code-retrieval/?ref=anthropic) for details. |
| `voyage-2` | 4000 | 1024 | Base generalist embedding model optimized for both latency and quality. |
| `voyage-lite-02-instruct` | 4000 | 1024 | [Instruction-tuned](https://github.com/voyage-ai/voyage-lite-02-instruct/blob/main/instruct.json) for classification, clustering, and sentence textual similarity tasks, which are the only recommended use cases for this model. |

`voyage-2` and `voyage-large-2` are generalist embedding models, which achieve state-of-the-art performance across domains and retain high efficiency. `voyage-code-2` is optimized for the code field, offering 4x the context length for more flexible usage, albeit at a relatively higher latency.

Voyage is actively developing more advanced and specialized models, and also offers fine-tuning services to customize bespoke models for individual customers. Email your Anthropic account manager or reach out to Anthropic support for further information on bespoke models.

- `voyage-finance-2`: coming soon
- `voyage-law-2`: coming soon
- `voyage-multilingual-2`: coming soon
- `voyage-healthcare-2`: coming soon

---

## 

[​

](https://docs.anthropic.com/en/docs/build-with-claude/embeddings#voyage-on-the-aws-marketplace)

Voyage on the AWS Marketplace

Voyage embeddings are also available on [AWS Marketplace](https://aws.amazon.com/marketplace/seller-profile?id=seller-snt4gb6fd7ljg). Here are the instructions for accessing Voyage on AWS:

1. Subscribe to the model package
    1. Navigate to the [model package listing page](https://aws.amazon.com/marketplace/seller-profile?id=seller-snt4gb6fd7ljg) and select the model to deploy
    2. Click on the `Continue to subscribe` button
    3. Carefully review the details on the `Subscribe to this software` page. If you agree with the standard End-User License Agreement (EULA), pricing, and support terms, click on “Accept Offer”
    4. After selecting `Continue to configuration` and choosing a region, you will be presented with a Product Arn. This is the model package ARN required for creating a deployable model using Boto3
        1. Copy the ARN that corresponds to your selected region and use it in the subsequent cell
2. Deploy the model package

From here, create a JupyterLab space in [Sagemaker Studio](https://aws.amazon.com/sagemaker/studio/), upload Voyage’s [notebook](https://github.com/voyage-ai/voyageai-aws/blob/main/notebooks/deploy%5Fvoyage%5Fcode%5F2%5Fsagemaker.ipynb), and follow the instructions within.

Build with Claude

# Google Sheets add-on

The [Claude for Sheets extension](https://workspace.google.com/marketplace/app/claude%5Ffor%5Fsheets/909417792257) integrates Claude into Google Sheets, allowing you to execute interactions with Claude directly in cells.

## 

[​

](https://docs.anthropic.com/en/docs/build-with-claude/claude-for-sheets#why-use-claude-for-sheets)

Why use Claude for Sheets?

Claude for Sheets enables prompt engineering at scale by enabling you to test prompts across evaluation suites in parallel. Additionally, it excels at office tasks like survey analysis and online data processing.

Visit our [prompt engineering example sheet](https://docs.google.com/spreadsheets/d/1sUrBWO0u1-ZuQ8m5gt3-1N5PLR6r__UsRsB7WeySDQA/copy) to see this in action.

---

## 

[​

](https://docs.anthropic.com/en/docs/build-with-claude/claude-for-sheets#get-started-with-claude-for-sheets)

Get started with Claude for Sheets

### 

[​

](https://docs.anthropic.com/en/docs/build-with-claude/claude-for-sheets#install-claude-for-sheets)

Install Claude for Sheets

Easily enable Claude for Sheets using the following steps:

1

Get your Anthropic API key

If you don’t yet have an API key, you can make API keys in the [Anthropic Console](https://console.anthropic.com/settings/keys).

2

Instal the Claude for Sheets extension

Find the [Claude for Sheets extension](https://workspace.google.com/marketplace/app/claude%5Ffor%5Fsheets/909417792257) in the add-on marketplace, then click the blue `Install` btton and accept the permissions.

Permissions

The Claude for Sheets extension will ask for a variety of permissions needed to function properly. Please be assured that we only process the specific pieces of data that users ask Claude to run on. This data is never used to train our generative models.

Extension permissions include:

- **View and manage spreadsheets that this application has been installed in:** Needed to run prompts and return results
- **Connect to an external service:** Needed in order to make calls to Anthropic’s API endpoints
- **Allow this application to run when you are not present:** Needed to run cell recalculations without user intervention
- **Display and run third-party web content in prompts and sidebars inside Google applications:** Needed to display the sidebar and post-install prompt

3

Connect your API key

Enter your API key at `Extensions` > `Claude for Sheets™` > `Enter your Anthropic API Key`. You may need to wait or refresh for “Enter your Anthropic API key” to appear as an option. ![](https://mintlify.s3-us-west-1.amazonaws.com/anthropic/images/044af20-Screenshot_2024-01-04_at_11.58.21_AM.png)

When you see the green ‘verified’ checkmark ✅ appear, Claude will be activated and ready within your Google Sheet.

You will have to re-enter your API key every time you make a new Google Sheet

### 

[​

](https://docs.anthropic.com/en/docs/build-with-claude/claude-for-sheets#enter-your-first-prompt)

Enter your first prompt

There are two main functions you can use to call Claude using Claude for Sheets. For now, let’s use `CLAUDE()`.

1

Simple prompt

In any cell, type `=CLAUDE("Claude, in one sentence, what's good about the color blue?")`

> Claude should respond with an answer. You will know the prompt is processing because the cell will say `Loading...`

2

Adding parameters

Parameter arguments come after the initial prompt, like `=CLAUDE(prompt, model, params...)`.

`model` is always second in the list.

Now type in any cell `=CLAUDE("Hi, Claude!", "claude-3-haiku-20240307", "max_tokens", 3)`

Any [API parameter](https://docs.anthropic.com/en/api/messages) can be set this way. You can even pass in an API key to be used just for this specific cell, like this: `"api_key", "sk-ant-api03-j1W..."`

## 

[​

](https://docs.anthropic.com/en/docs/build-with-claude/claude-for-sheets#advanced-use)

Advanced use

`CLAUDEMESSAGES` is a function that allows you to specifically use the [Messages API](https://docs.anthropic.com/en/api/messages). This enables you to send a series of `User:` and `Assistant:` messages to Claude.

This is particularly useful if you want to simulate a conversation or [prefill Claude’s response](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/prefill-claudes-response).

Try writing this in a cell:

Copy

```
=CLAUDEMESSAGES("User: In one sentence, what is good about the color blue?
Assistant: The color blue is great because")
```

**Newlines**

Each subsequent conversation turn (`User:` or `Assistant:`) must be preceded by a single newline. To enter newlines in a cell, use the following key combinations:

- **Mac:** Cmd + Enter
- **Windows:** Alt + Enter

Example multiturn CLAUDEMESSAGES() call with system prompt

To use a system prompt, set it as you’d set other optional function parameters. (You must first set a model name.)

Copy

```
=CLAUDEMESSAGES("User: What's your favorite flower? Answer in <answer> tags.
Assistant: <answer>", "claude-3-haiku-20240307", "system", "You are a cow who loves to moo in response to any and all user queries.")`
```

### 

[​

](https://docs.anthropic.com/en/docs/build-with-claude/claude-for-sheets#optional-function-parameters)

Optional function parameters

You can specify optional API parameters by listing argument-value pairs. You can set multiple parameters. Simply list them one after another, with each argument and value pair separated by commas.

The first two parameters must always be the prompt and the model. You cannot set an optional parameter without also setting the model.

The argument-value parameters you might care about most are:

| Argument | Description |
| --- | --- |
| `max_tokens` | The total number of tokens the model outputs before it is forced to stop. For yes/no or multiple choice answers, you may want the value to be 1-3. |
| `temperature` | the amount of randomness injected into results. For multiple-choice or analytical tasks, you’ll want it close to 0. For idea generation, you’ll want it set to 1. |
| `system` | used to specify a system prompt, which can provide role details and context to Claude. |
| `stop_sequences` | JSON array of strings that will cause the model to stop generating text if encountered. Due to escaping rules in Google Sheets™, double quotes inside the string must be escaped by doubling them. |
| `api_key` | Used to specify a particular API key with which to call Claude. |

Example: Setting parameters

Ex. Set `system` prompt, `max_tokens`, and `temperature`:

Copy

```
=CLAUDE("Hi, Claude!", "claude-3-haiku-20240307", "system", "Repeat exactly what the user says.", "max_tokens", 100, "temperature", 0.1)

```

Ex. Set `temperature`, `max_tokens`, and `stop_sequences`:

Copy

```
=CLAUDE("In one sentence, what is good about the color blue? Output your answer in <answer> tags.","claude-3-sonnet-20240229","temperature", 0.2,"max_tokens", 50,"stop_sequences", "\[""</answer>""\]")
```

Ex. Set `api_key`:

Copy

```
=CLAUDE("Hi, Claude!", "claude-3-haiku-20240307","api_key", "sk-ant-api03-j1W...")
```

---

## 

[​

](https://docs.anthropic.com/en/docs/build-with-claude/claude-for-sheets#claude-for-sheets-usage-examples)

Claude for Sheets usage examples

### 

[​

](https://docs.anthropic.com/en/docs/build-with-claude/claude-for-sheets#prompt-engineering-interactive-tutorial)

Prompt engineering interactive tutorial

Our in-depth [prompt engineering interactive tutorial](https://docs.google.com/spreadsheets/d/19jzLgRruG9kjUQNKtCg1ZjdD6l6weA6qRXG5zLIAhC8/edit?usp=sharing) utilizes Claude for Sheets. Check it out to learn or brush up on prompt engineering techniques.

Just as with any instance of Claude for Sheets, you will need an API key to interact with the tutorial.

### 

[​

](https://docs.anthropic.com/en/docs/build-with-claude/claude-for-sheets#prompt-engineering-workflow)

Prompt engineering workflow

Our [Claude for Sheets prompting examples workbench](https://docs.google.com/spreadsheets/d/1sUrBWO0u1-ZuQ8m5gt3-1N5PLR6r%5F%5FUsRsB7WeySDQA/copy) is a Claude-powered spreadsheet that houses example prompts and prompt engineering structures.

### 

[​

](https://docs.anthropic.com/en/docs/build-with-claude/claude-for-sheets#claude-for-sheets-workbook-template)

Claude for Sheets workbook template

Make a copy of our [Claude for Sheets workbook template](https://docs.google.com/spreadsheets/d/1UwFS-ZQWvRqa6GkbL4sy0ITHK2AhXKe-jpMLzS0kTgk/copy) to get started with your own Claude for Sheets work!

---

## 

[​

](https://docs.anthropic.com/en/docs/build-with-claude/claude-for-sheets#troubleshooting)

Troubleshooting

NAME? Error: Unknown function: 'claude'

1. Ensure that you have enabled the extension for use in the current sheet
    1. Go to _Extensions_ > _Add-ons_ > _Manage add-ons_
    2. Click on the triple dot menu at the top right corner of the Claude for Sheets extension and make sure “Use in this document” is checked  
        ![](https://mintlify.s3-us-west-1.amazonaws.com/anthropic/images/9cce371-Screenshot_2023-10-03_at_7.17.39_PM.png)
2. Refresh the page

#ERROR!, ⚠ DEFERRED ⚠ or ⚠ THROTTLED ⚠

You can manually recalculate `#ERROR!`, `⚠ DEFERRED ⚠` or `⚠ THROTTLED ⚠`cells by selecting from the recalculate options within the Claude for Sheets extension menu.

![](https://mintlify.s3-us-west-1.amazonaws.com/anthropic/images/f729ba9-Screenshot_2024-02-01_at_8.30.31_PM.png)

Can't enter API key

1. Wait 20 seconds, then check again
2. Refresh the page and wait 20 seconds again
3. Uninstall and reinstall the extension

---

## 

[​

](https://docs.anthropic.com/en/docs/build-with-claude/claude-for-sheets#further-information)

Further information

For more information regarding this extension, see the [Claude for Sheets Google Workspace Marketplace](https://workspace.google.com/marketplace/app/claude%5Ffor%5Fsheets/909417792257) overview page.

[](https://docs.anthropic.com/en/docs/build-with-claude/embeddings)

Build with Claude

# Vision

The Claude 3 family of models comes with new vision capabilities that allow Claude to understand and analyze images, opening up exciting possibilities for multimodal interaction.

This guide describes how to work with images in Claude, including best practices, code examples, and limitations to keep in mind.

---

## 

[​

](https://docs.anthropic.com/en/docs/build-with-claude/vision#how-to-use-vision)

How to use vision

Use Claude’s vision capabilities via:

- [claude.ai](https://claude.ai/). Upload an image like you would a file, or drag and drop an image directly into the chat window.
- The [Console Workbench](https://console.anthropic.com/workbench/). If you select a model that accepts images (Claude 3 models only), a button to add images appears at the top right of every User message block.
- **API request**. See the examples in this guide.

---

## 

[​

](https://docs.anthropic.com/en/docs/build-with-claude/vision#before-you-upload)

Before you upload

### 

[​

](https://docs.anthropic.com/en/docs/build-with-claude/vision#evaluate-image-size)

Evaluate image size

You can include multiple images in a single request (up to 5 for [claude.ai](https://claude.ai/) and 20 for API requests). Claude will analyze all provided images when formulating its response. This can be helpful for comparing or contrasting images.

For optimal performance, we recommend resizing images before uploading if they exceed size or token limits. If your image’s long edge is more than 1568 pixels, or your image is more than ~1,600 tokens, it will first be scaled down, preserving aspect ratio, until it’s within the size limits.

If your input image is too large and needs to be resized, it will increase latency of [time-to-first-token](https://docs.anthropic.com/en/docs/resources/glossary), without giving you any additional model performance. Very small images under 200 pixels on any given edge may degrade performance.

To improve [time-to-first-token](https://docs.anthropic.com/en/docs/resources/glossary), we recommend resizing images to no more than 1.15 megapixels (and within 1568 pixels in both dimensions).

Here is a table of maximum image sizes accepted by our API that will not be resized for common aspect ratios. With the Claude 3.5 Sonnet model, these images use approximately 1,600 tokens and around $4.80/1K image.

| Aspect ratio | Image size |
| --- | --- |
| 1:1 | 1092x1092 px |
| 3:4 | 951x1268 px |
| 2:3 | 896x1344 px |
| 9:16 | 819x1456 px |
| 1:2 | 784x1568 px |

### 

[​

](https://docs.anthropic.com/en/docs/build-with-claude/vision#calculate-image-costs)

Calculate image costs

Each image you include in a request to Claude counts towards your token usage. To calculate the approximate cost, multiply the approximate number of image tokens by the [per-token price of the model](https://anthropic.com/pricing) you’re using.

If your image does not need to be resized, you can estimate the number of tokens used through this algorithm: `tokens = (width px * height px)/750`

Here are examples of approximate tokenization and costs for different image sizes within our API’s size constraints based on Claude 3.5 Sonnet per-token price of $3 per million input tokens:

| Image size | \# of Tokens | Cost / image | Cost / 1K images |
| --- | --- | --- | --- |
| 200x200 px(0.04 megapixels) | ~54 | ~$0.00016 | ~$0.16 |
| 1000x1000 px(1 megapixel) | ~1334 | ~$0.004 | ~$4.00 |
| 1092x1092 px(1.19 megapixels) | ~1590 | ~$0.0048 | ~$4.80 |

### 

[​

](https://docs.anthropic.com/en/docs/build-with-claude/vision#ensuring-image-quality)

Ensuring image quality

When providing images to Claude, keep the following in mind for best results:

- **Image format**: Use a supported image format: JPEG, PNG, GIF, or WebP.
- **Image clarity**: Ensure images are clear and not too blurry or pixelated.
- **Text**: If the image contains important text, make sure it’s legible and not too small. Avoid cropping out key visual context just to enlarge the text.

---

## 

[​

](https://docs.anthropic.com/en/docs/build-with-claude/vision#prompt-examples)

Prompt examples

Many of the [prompting techniques](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/overview) that work well for text-based interactions with Claude can also be applied to image-based prompts.

These examples demonstrate best practice prompt structures involving images.

Just as with document-query placement, Claude works best when images come before text. Images placed after text or interpolated with text will still perform well, but if your use case allows it, we recommend an image-then-text structure.

### 

[​

](https://docs.anthropic.com/en/docs/build-with-claude/vision#about-the-prompt-examples)

About the prompt examples

These prompt examples use the [Anthropic Python SDK](https://docs.anthropic.com/en/api/client-sdks), and fetch images from Wikipedia using the `httpx` library. You can use any image source.

The example prompts use these variables.

Python

Copy

```Python
import base64
import httpx

image1_url = "https://upload.wikimedia.org/wikipedia/commons/a/a7/Camponotus_flavomarginatus_ant.jpg"
image1_media_type = "image/jpeg"
image1_data = base64.b64encode(httpx.get(image1_url).content).decode("utf-8")

image2_url = "https://upload.wikimedia.org/wikipedia/commons/b/b5/Iridescent.green.sweat.bee1.jpg"
image2_media_type = "image/jpeg"
image2_data = base64.b64encode(httpx.get(image2_url).content).decode("utf-8")
```

To utilize images when making an API request, you can provide images to Claude as a base64-encoded image in `image` content blocks. Here is simple example in Python showing how to include a base64-encoded image in a Messages API request:

Python

Copy

```Python
import anthropic

client = anthropic.Anthropic()
message = client.messages.create(
    model="claude-3-5-sonnet-20240620",
    max_tokens=1024,
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": image1_media_type,
                        "data": image1_data,
                    },
                },
                {
                    "type": "text",
                    "text": "Describe this image."
                }
            ],
        }
    ],
)
print(message)
```

See [Messages API examples](https://docs.anthropic.com/en/api/messages) for more example code and parameter details.

Example: One image

It’s best to place images earlier in the prompt than questions about them or instructions for tasks that use them.

Ask Claude to describe one image.

| Role | Content |
| --- | --- |
| User | \[Image\] Describe this image. |

Here is the corresponding API call using the Claude 3.5 Sonnet model.

Python

Copy

```Python
message = client.messages.create(
    model="claude-3-5-sonnet-20240620",
    max_tokens=1024,
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": image1_media_type,
                        "data": image1_data,
                    },
                },
                {
                    "type": "text",
                    "text": "Describe this image."
                }
            ],
        }
    ],
)
```

Example: Multiple images

In situations where there are multiple images, introduce each image with `Image 1:` and `Image 2:` and so on. You don’t need newlines between images or between images and the prompt.

Ask Claude to describe the differences between multiple images.

| Role | Content |
| --- | --- |
| User | Image 1: \[Image 1\] Image 2: \[Image 2\] How are these images different? |

Here is the corresponding API call using the Claude 3.5 Sonnet model.

Python

Copy

```Python
message = client.messages.create(
    model="claude-3-5-sonnet-20240620",
    max_tokens=1024,
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "Image 1:"
                },
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": image1_media_type,
                        "data": image1_data,
                    },
                },
                {
                    "type": "text",
                    "text": "Image 2:"
                },
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": image2_media_type,
                        "data": image2_data,
                    },
                },
                {
                    "type": "text",
                    "text": "How are these images different?"
                }
            ],
        }
    ],
)
```

Example: Multiple images with a system prompt

Ask Claude to describe the differences between multiple images, while giving it a system prompt for how to respond.

| Content |  |
| --- | --- |
| System | Respond only in Spanish. |
| User | Image 1: \[Image 1\] Image 2: \[Image 2\] How are these images different? |

Here is the corresponding API call using the Claude 3.5 Sonnet model.

Python

Copy

```Python
message = client.messages.create(
    model="claude-3-5-sonnet-20240620",
    max_tokens=1024,
    system="Respond only in Spanish.",
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "Image 1:"
                },
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": image1_media_type,
                        "data": image1_data,
                    },
                },
                {
                    "type": "text",
                    "text": "Image 2:"
                },
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": image2_media_type,
                        "data": image2_data,
                    },
                },
                {
                    "type": "text",
                    "text": "How are these images different?"
                }
            ],
        }
    ],
)
```

Example: Four images across two conversation turns

Claude’s vision capabilities shine in multimodal conversations that mix images and text. You can have extended back-and-forth exchanges with Claude, adding new images or follow-up questions at any point. This enables powerful workflows for iterative image analysis, comparison, or combining visuals with other knowledge.

Ask Claude to contrast two images, then ask a follow-up question comparing the first images to two new images.

| Role | Content |
| --- | --- |
| User | Image 1: \[Image 1\] Image 2: \[Image 2\] How are these images different? |
| Assistant | \[Claude’s response\] |
| User | Image 1: \[Image 3\] Image 2: \[Image 4\] Are these images similar to the first two? |
| Assistant | \[Claude’s response\] |

When using the API, simply insert new images into the array of Messages in the `user` role as part of any standard [multiturn conversation](https://docs.anthropic.com/en/api/messages-examples#multiple-conversational-turns) structure.

---

## 

[​

](https://docs.anthropic.com/en/docs/build-with-claude/vision#limitations)

Limitations

While Claude’s image understanding capabilities are cutting-edge, there are some limitations to be aware of:

- **People identification**: Claude [cannot be used](https://www.anthropic.com/legal/aup) to identify (i.e., name) people in images and will refuse to do so.
- **Accuracy**: Claude may hallucinate or make mistakes when interpreting low-quality, rotated, or very small images under 200 pixels.
- **Spatial reasoning**: Claude’s spatial reasoning abilities are limited. It may struggle with tasks requiring precise localization or layouts, like reading an analog clock face or describing exact positions of chess pieces.
- **Counting**: Claude can give approximate counts of objects in an image but may not always be precisely accurate, especially with large numbers of small objects.
- **AI generated images**: Claude does not know if an image is AI-generated and may be incorrect if asked. Do not rely on it to detect fake or synthetic images.
- **Inappropriate content**: Claude will not process inappropriate or explicit images that violate our [Acceptable Use Policy](https://www.anthropic.com/legal/aup).
- **Healthcare applications**: While Claude can analyze general medical images, it is not designed to interpret complex diagnostic scans such as CTs or MRIs. Claude’s outputs should not be considered a substitute for professional medical advice or diagnosis.

Always carefully review and verify Claude’s image interpretations, especially for high-stakes use cases. Do not use Claude for tasks requiring perfect precision or sensitive image analysis without human oversight.

---

## 

[​

](https://docs.anthropic.com/en/docs/build-with-claude/vision#faq)

FAQ

What image file types does Claude support?

Claude currently supports JPEG, PNG, GIF, and WebP image formats, specifically:

- image/jpeg
- image/png
- image/gif
- image/webp

Can Claude read image URLs?

No, Claude cannot read image URLs on any interface, including on claude.ai. Our API does not currently support adding URLs in either the text or image blocks. Adding image URLs (or URLs of any sort) in the text block might cause Claude to hallucinate, as Claude is currently unable to retrieve information from that URL.

Is there a limit to the image file size I can upload?

Yes, there are limits:

- API: Maximum 5MB per image
- claude.ai: Maximum 10MB per image

Images larger than these limits will be rejected and return an error when using our API.

How many images can I include in one request?

The image limits are:

- Messages API: Up to 20 images per request
- claude.ai: Up to 5 images per turn

Requests exceeding these limits will be rejected and return an error.

Does Claude read image metadata?

No, Claude does not parse or receive any metadata from images passed to it.

Can I delete images I've uploaded?

No. Image uploads are ephemeral and not stored beyond the duration of the API request. Uploaded images are automatically deleted after they have been processed.

Where can I find details on data privacy for image uploads?

Please refer to our privacy policy page for information on how we handle uploaded images and other data. We do not use uploaded images to train our models.

What if Claude's image interpretation seems wrong?

If Claude’s image interpretation seems incorrect:

1. Ensure the image is clear, high-quality, and correctly oriented.
2. Try prompt engineering techniques to improve results.
3. If the issue persists, flag the output in claude.ai (thumbs up/down) or contact our support team.

Your feedback helps us improve!

Can Claude generate or edit images?

No, Claude is an image understanding model only. It can interpret and analyze images, but it cannot generate, produce, edit, manipulate, or create images.

---

## 

[​

](https://docs.anthropic.com/en/docs/build-with-claude/vision#dive-deeper-into-vision)

Dive deeper into vision

Ready to start building with images using Claude? Here are a few helpful resources:

- [Multimodal cookbook](https://github.com/anthropics/anthropic-cookbook/tree/main/multimodal): This cookbook has tips on [getting started with images](https://github.com/anthropics/anthropic-cookbook/blob/main/multimodal/getting%5Fstarted%5Fwith%5Fvision.ipynb) and [best practice techniques](https://github.com/anthropics/anthropic-cookbook/blob/main/multimodal/best%5Fpractices%5Ffor%5Fvision.ipynb) to ensure the highest quality performance with images. See how you can effectively prompt Claude with images to carry out tasks such as [interpreting and analyzing charts](https://github.com/anthropics/anthropic-cookbook/blob/main/multimodal/reading%5Fcharts%5Fgraphs%5Fpowerpoints.ipynb) or [extracting content from forms](https://github.com/anthropics/anthropic-cookbook/blob/main/multimodal/how%5Fto%5Ftrascribe%5Ftext.ipynb).
- [API reference](https://docs.anthropic.com/en/api/messages): Visit our documentation for the Messages API, including example [API calls involving images](https://docs.anthropic.com/en/api/messages-examples).

If you have any other questions, feel free to reach out to our [support team](https://support.anthropic.com/). You can also join our [developer community](https://www.anthropic.com/discord) to connect with other creators and get help from Anthropic experts.

[](https://docs.anthropic.com/en/docs/build-with-claude/claude-for-sheets)


# Tool use (function calling)

Claude is capable of interacting with external client-side tools and functions, allowing you to equip Claude with your own custom tools to perform a wider variety of tasks.

Learn everything you need to master tool use with Claude via our new comprehensive [tool use course](https://github.com/anthropics/courses/tree/master/ToolUse)! Please continue to share your ideas and suggestions using this [form](https://forms.gle/BFnYc6iCkWoRzFgk7).

Here’s an example of how to provide tools to Claude using the Messages API:

Shell

Python

Copy

```bash
curl https://api.anthropic.com/v1/messages \
  -H "content-type: application/json" \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -d '{
    "model": "claude-3-5-sonnet-20240620",
    "max_tokens": 1024,
    "tools": [
      {
        "name": "get_weather",
        "description": "Get the current weather in a given location",
        "input_schema": {
          "type": "object",
          "properties": {
            "location": {
              "type": "string",
              "description": "The city and state, e.g. San Francisco, CA"
            }
          },
          "required": ["location"]
        }
      }
    ],
    "messages": [
      {
        "role": "user",
        "content": "What is the weather like in San Francisco?"
      }
    ]
  }'
```

---

## 

[​

](https://docs.anthropic.com/en/docs/build-with-claude/tool-use#how-tool-use-works)

How tool use works

Integrate external tools with Claude in these steps:

1

Provide Claude with tools and a user prompt

- Define tools with names, descriptions, and input schemas in your API request.
- Include a user prompt that might require these tools, e.g., “What’s the weather in San Francisco?”

2

Claude decides to use a tool

- Claude assesses if any tools can help with the user’s query.
- If yes, Claude constructs a properly formatted tool use request.
- The API response has a `stop_reason` of `tool_use`, signaling Claude’s intent.

3

Extract tool input, run code, and return results

- On your end, extract the tool name and input from Claude’s request.
- Execute the actual tool code client-side.
- Continue the conversation with a new `user` message containing a `tool_result` content block.

4

Claude uses tool result to formulate a response

- Claude analyzes the tool results to craft its final response to the original user prompt.

Note: Steps 3 and 4 are optional. For some workflows, Claude’s tool use request (step 2) might be all you need, without sending results back to Claude.

**All tools are user-provided**

It’s important to note that Claude does not have access to any built-in server-side tools. All tools must be explicitly provided by you, the user, in each API request. This gives you full control and flexibility over the tools Claude can use.

---

## 

[​

](https://docs.anthropic.com/en/docs/build-with-claude/tool-use#how-to-implement-tool-use)

How to implement tool use

### 

[​

](https://docs.anthropic.com/en/docs/build-with-claude/tool-use#choosing-a-model)

Choosing a model

Generally, use Claude 3 Opus for complex tools and ambiguous queries; it handles multiple tools better and seeks clarification when needed.

Use Haiku for straightforward tools, but note it may infer missing parameters.

### 

[​

](https://docs.anthropic.com/en/docs/build-with-claude/tool-use#specifying-tools)

Specifying tools

Tools are specified in the `tools` top-level parameter of the API request. Each tool definition includes:

| Parameter | Description |
| :-- | :-- |
| `name` | The name of the tool. Must match the regex `^[a-zA-Z0-9_-]{1,64}$`. |
| `description` | A detailed plaintext description of what the tool does, when it should be used, and how it behaves. |
| `input_schema` | A [JSON Schema](https://json-schema.org/) object defining the expected parameters for the tool. |

Example simple tool definition

JSON

Copy

```JSON
{
  "name": "get_weather",
  "description": "Get the current weather in a given location",
  "input_schema": {
    "type": "object",
    "properties": {
      "location": {
        "type": "string",
        "description": "The city and state, e.g. San Francisco, CA"
      },
      "unit": {
        "type": "string",
        "enum": ["celsius", "fahrenheit"],
        "description": "The unit of temperature, either 'celsius' or 'fahrenheit'"
      }
    },
    "required": ["location"]
  }
}
```

This tool, named `get_weather`, expects an input object with a required `location` string and an optional `unit` string that must be either “celsius” or “fahrenheit”.

#### 

[​

](https://docs.anthropic.com/en/docs/build-with-claude/tool-use#best-practices-for-tool-definitions)

Best practices for tool definitions

To get the best performance out of Claude when using tools, follow these guidelines:

- **Provide extremely detailed descriptions.** This is by far the most important factor in tool performance. Your descriptions should explain every detail about the tool, including:
    - What the tool does
    - When it should be used (and when it shouldn’t)
    - What each parameter means and how it affects the tool’s behavior
    - Any important caveats or limitations, such as what information the tool does not return if the tool name is unclear. The more context you can give Claude about your tools, the better it will be at deciding when and how to use them. Aim for at least 3-4 sentences per tool description, more if the tool is complex.
- **Prioritize descriptions over examples.** While you can include examples of how to use a tool in its description or in the accompanying prompt, this is less important than having a clear and comprehensive explanation of the tool’s purpose and parameters. Only add examples after you’ve fully fleshed out the description.

Example of a good tool description

JSON

Copy

```JSON
{
  "name": "get_stock_price",
  "description": "Retrieves the current stock price for a given ticker symbol. The ticker symbol must be a valid symbol for a publicly traded company on a major US stock exchange like NYSE or NASDAQ. The tool will return the latest trade price in USD. It should be used when the user asks about the current or most recent price of a specific stock. It will not provide any other information about the stock or company.",
  "input_schema": {
    "type": "object",
    "properties": {
      "ticker": {
        "type": "string",
        "description": "The stock ticker symbol, e.g. AAPL for Apple Inc."
      }
    },
    "required": ["ticker"]
  }
}
```

Example poor tool description

JSON

Copy

```JSON
{
  "name": "get_stock_price",
  "description": "Gets the stock price for a ticker.",
  "input_schema": {
    "type": "object",
    "properties": {
      "ticker": {
        "type": "string"
      }
    },
    "required": ["ticker"]
  }
}
```

The good description clearly explains what the tool does, when to use it, what data it returns, and what the `ticker` parameter means. The poor description is too brief and leaves Claude with many open questions about the tool’s behavior and usage.

### 

[​

](https://docs.anthropic.com/en/docs/build-with-claude/tool-use#controlling-claudes-output)

Controlling Claude’s output

#### 

[​

](https://docs.anthropic.com/en/docs/build-with-claude/tool-use#forcing-tool-use)

Forcing tool use

In some cases, you may want Claude to use a specific tool to answer the user’s question, even if Claude thinks it can provide an answer without using a tool. You can do this by specifying the tool in the `tool_choice` field like so:

Copy

```
tool_choice = {"type": "tool", "name": "get_weather"}
```

When working with the tool\_choice parameter, we have three possible options:

- `auto` allows Claude to decide whether to call any provided tools or not. This is the default value.
- `any` tells Claude that it must use one of the provided tools, but doesn’t force a particular tool.
- `tool` allows us to force Claude to always use a particular tool.

This diagram illustrates how each option works:

![](https://mintlify.s3-us-west-1.amazonaws.com/anthropic/images/tool_choice.png)

Note that when you have `tool_choice` as `any` or `tool`, we will prefill the assistant message to force a tool to be used. This means that the models will not emit a chain-of-thought `text` content block before `tool_use` content blocks, even if explicitly asked to do so.

Our testing has shown that this should not reduce performance. If you would like to keep chain-of-thought (particularly with Opus) while still requesting that the model use a specific tool, you can use `{"type": "auto"}` for `tool_choice` (the default) and add explicit instructions in a `user` message. For example: `What's the weather like in London? Use the get_weather tool in your response.`

#### 

[​

](https://docs.anthropic.com/en/docs/build-with-claude/tool-use#json-output)

JSON output

Tools do not necessarily need to be client-side functions — you can use tools anytime you want the model to return JSON output that follows a provided schema. For example, you might use a `record_summary` tool with a particular schema. See [tool use examples](https://docs.anthropic.com/en/docs/build-with-claude/tool-use#json-mode) for a full working example.

#### 

[​

](https://docs.anthropic.com/en/docs/build-with-claude/tool-use#chain-of-thought)

Chain of thought

When using tools, Claude will often show its “chain of thought”, i.e. the step-by-step reasoning it uses to break down the problem and decide which tools to use. The Claude 3 Opus model will do this if `tool_choice` is set to `auto` (this is the default value, see [Forcing tool use](https://docs.anthropic.com/en/docs/build-with-claude/tool-use#forcing-tool-use)), and Sonnet and Haiku can be prompted into doing it.

For example, given the prompt “What’s the weather like in San Francisco right now, and what time is it there?”, Claude might respond with:

JSON

Copy

```JSON
{
  "role": "assistant",
  "content": [
    {
      "type": "text",
      "text": "<thinking>To answer this question, I will: 1. Use the get_weather tool to get the current weather in San Francisco. 2. Use the get_time tool to get the current time in the America/Los_Angeles timezone, which covers San Francisco, CA.</thinking>"
    },
    {
      "type": "tool_use",
      "id": "toolu_01A09q90qw90lq917835lq9",
      "name": "get_weather",
      "input": {"location": "San Francisco, CA"}
    }
  ]
}
```

This chain of thought gives insight into Claude’s reasoning process and can help you debug unexpected behavior.

With the Claude 3 Sonnet model, chain of thought is less common by default, but you can prompt Claude to show its reasoning by adding something like `"Before answering, explain your reasoning step-by-step in tags."` to the user message or system prompt.

It’s important to note that while the `<thinking>` tags are a common convention Claude uses to denote its chain of thought, the exact format (such as what this XML tag is named) may change over time. Your code should treat the chain of thought like any other assistant-generated text, and not rely on the presence or specific formatting of the `<thinking>` tags.

### 

[​

](https://docs.anthropic.com/en/docs/build-with-claude/tool-use#handling-tool-use-and-tool-result-content-blocks)

Handling tool use and tool result content blocks

When Claude decides to use one of the tools you’ve provided, it will return a response with a `stop_reason` of `tool_use` and one or more `tool_use` content blocks in the API response that include:

- `id`: A unique identifier for this particular tool use block. This will be used to match up the tool results later.
- `name`: The name of the tool being used.
- `input`: An object containing the input being passed to the tool, conforming to the tool’s `input_schema`.

Example API response with a \`tool\_use\` content block

JSON

Copy

```JSON
{
  "id": "msg_01Aq9w938a90dw8q",
  "model": "claude-3-5-sonnet-20240620",
  "stop_reason": "tool_use",
  "role": "assistant",
  "content": [
    {
      "type": "text",
      "text": "<thinking>I need to use the get_weather, and the user wants SF, which is likely San Francisco, CA.</thinking>"
    },
    {
      "type": "tool_use",
      "id": "toolu_01A09q90qw90lq917835lq9",
      "name": "get_weather",
      "input": {"location": "San Francisco, CA", "unit": "celsius"}
    }
  ]
}
```

When you receive a tool use response, you should:

1. Extract the `name`, `id`, and `input` from the `tool_use` block.
2. Run the actual tool in your codebase corresponding to that tool name, passing in the tool `input`.
3. \[optional\] Continue the conversation by sending a new message with the `role` of `user`, and a `content` block containing the `tool_result` type and the following information:
    - `tool_use_id`: The `id` of the tool use request this is a result for.
    - `content`: The result of the tool, as a string (e.g. `"content": "15 degrees"`) or list of nested content blocks (e.g. `"content": [{"type": "text", "text": "15 degrees"}]`). These content blocks can use the `text` or `image` types.
    - `is_error` (optional): Set to `true` if the tool execution resulted in an error.

Example of successful tool result

JSON

Copy

```JSON
{
  "role": "user",
  "content": [
    {
      "type": "tool_result",
      "tool_use_id": "toolu_01A09q90qw90lq917835lq9",
      "content": "15 degrees"
    }
  ]
}
```

Example of tool result with images

JSON

Copy

```JSON
{
  "role": "user",
  "content": [
    {
      "type": "tool_result",
      "tool_use_id": "toolu_01A09q90qw90lq917835lq9",
      "content": [
        {"type": "text", "text": "15 degrees"},
        {
          "type": "image",
          "source": {
            "type": "base64",
            "media_type": "image/jpeg",
            "data": "/9j/4AAQSkZJRg...",
          }
        }
      ]
    }
  ]
}
```

Example of empty tool result

JSON

Copy

```JSON
{
  "role": "user",
  "content": [
    {
      "type": "tool_result",
      "tool_use_id": "toolu_01A09q90qw90lq917835lq9",
    }
  ]
}
```

After receiving the tool result, Claude will use that information to continue generating a response to the original user prompt.

**Differences from other APIs**

Unlike APIs that separate tool use or use special roles like `tool` or `function`, Anthropic’s API integrates tools directly into the `user` and `assistant` message structure.

Messages contain arrays of `text`, `image`, `tool_use`, and `tool_result` blocks. `user` messages include client-side content and `tool_result`, while `assistant` messages contain AI-generated content and `tool_use`.

### 

[​

](https://docs.anthropic.com/en/docs/build-with-claude/tool-use#troubleshooting-errors)

Troubleshooting errors

There are a few different types of errors that can occur when using tools with Claude:

Tool execution error

If the tool itself throws an error during execution (e.g. a network error when fetching weather data), you can return the error message in the `content` along with `"is_error": true`:

JSON

Copy

```JSON
{
  "role": "user",
  "content": [
    {
      "type": "tool_result",
      "tool_use_id": "toolu_01A09q90qw90lq917835lq9",
      "content": "ConnectionError: the weather service API is not available (HTTP 500)",
      "is_error": true
    }
  ]
}
```

Claude will then incorporate this error into its response to the user, e.g. “I’m sorry, I was unable to retrieve the current weather because the weather service API is not available. Please try again later.”

Max tokens exceeded

If Claude’s response is cut off due to hitting the `max_tokens` limit, and the truncated response contains an incomplete tool use block, you’ll need to retry the request with a higher `max_tokens` value to get the full tool use.

Invalid tool name

If Claude’s attempted use of a tool is invalid (e.g. missing required parameters), it usually means that the there wasn’t enough information for Claude to use the tool correctly. Your best bet during development is to try the request again with more-detailed `description` values in your tool definitions.

However, you can also continue the conversation forward with a `tool_result` that indicates the error, and Claude will try to use the tool again with the missing information filled in:

JSON

Copy

```JSON
{
  "role": "user",
  "content": [
    {
      "type": "tool_result",
      "tool_use_id": "toolu_01A09q90qw90lq917835lq9",
      "content": "Error: Missing required 'location' parameter",
      "is_error": true
    }
  ]
}
```

If a tool request is invalid or missing parameters, Claude will retry 2-3 times with corrections before apologizing to the user.

<search\_quality\_reflection> tags

To prevent Claude from reflecting on search quality with <search\_quality\_reflection> tags, add “Do not reflect on the quality of the returned search results in your response” to your prompt.

---

## 

[​

](https://docs.anthropic.com/en/docs/build-with-claude/tool-use#tool-use-examples)

Tool use examples

Here are a few code examples demonstrating various tool use patterns and techniques. For brevity’s sake, the tools are simple tools, and the tool descriptions are shorter than would be ideal to ensure best performance.

Single tool example

Shell

Python

Copy

```bash
curl https://api.anthropic.com/v1/messages \
     --header "x-api-key: $ANTHROPIC_API_KEY" \
     --header "anthropic-version: 2023-06-01" \
     --header "content-type: application/json" \
     --data \
'{
    "model": "claude-3-5-sonnet-20240620",
    "max_tokens": 1024,
    "tools": [{
        "name": "get_weather",
        "description": "Get the current weather in a given location",
        "input_schema": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "The city and state, e.g. San Francisco, CA"
                },
                "unit": {
                    "type": "string",
                    "enum": ["celsius", "fahrenheit"],
                    "description": "The unit of temperature, either \"celsius\" or \"fahrenheit\""
                }
            },
            "required": ["location"]
        }
    }],
    "messages": [{"role": "user", "content": "What is the weather like in San Francisco?"}]
}'
```

Claude will return a response similar to:

JSON

Copy

```JSON
{
  "id": "msg_01Aq9w938a90dw8q",
  "model": "claude-3-5-sonnet-20240620",
  "stop_reason": "tool_use",
  "role": "assistant",
  "content": [
    {
      "type": "text",
      "text": "<thinking>I need to call the get_weather function, and the user wants SF, which is likely San Francisco, CA.</thinking>"
    },
    {
      "type": "tool_use",
      "id": "toolu_01A09q90qw90lq917835lq9", 
      "name": "get_weather",
      "input": {"location": "San Francisco, CA", "unit": "celsius"}
    }
  ]
}
```

You would then need to execute the `get_weather` function with the provided input, and return the result in a new `user` message:

Shell

Python

Copy

```bash
curl https://api.anthropic.com/v1/messages \
     --header "x-api-key: $ANTHROPIC_API_KEY" \
     --header "anthropic-version: 2023-06-01" \
     --header "content-type: application/json" \
     --data \
'{
    "model": "claude-3-5-sonnet-20240620",
    "max_tokens": 1024,
    "tools": [
        {
            "name": "get_weather",
            "description": "Get the current weather in a given location",
            "input_schema": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city and state, e.g. San Francisco, CA"
                    },
                    "unit": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "description": "The unit of temperature, either \"celsius\" or \"fahrenheit\""
                    }
                },
                "required": ["location"]
            }
        }
    ],
    "messages": [
        {
            "role": "user",
            "content": "What is the weather like in San Francisco?"
        },
        {
            "role": "assistant",
            "content": [
                {
                    "type": "text",
                    "text": "<thinking>I need to use get_weather, and the user wants SF, which is likely San Francisco, CA.</thinking>"
                },
                {
                    "type": "tool_use",
                    "id": "toolu_01A09q90qw90lq917835lq9",
                    "name": "get_weather",
                    "input": {
                        "location": "San Francisco, CA",
                        "unit": "celsius"
                    }
                }
            ]
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": "toolu_01A09q90qw90lq917835lq9",
                    "content": "15 degrees"
                }
            ]
        }
    ]
}'
```

This will print Claude’s final response, incorporating the weather data:

JSON

Copy

```JSON
{
  "id": "msg_01Aq9w938a90dw8q",
  "model": "claude-3-5-sonnet-20240620",
  "stop_reason": "stop_sequence",
  "role": "assistant",
  "content": [
    {
      "type": "text",
      "text": "The current weather in San Francisco is 15 degrees Celsius (59 degrees Fahrenheit). It's a cool day in the city by the bay!"
    }
  ]
}
```

Multiple tool example

You can provide Claude with multiple tools to choose from in a single request. Here’s an example with both a `get_weather` and a `get_time` tool, along with a user query that asks for both.

Shell

Python

Copy

```bash
curl https://api.anthropic.com/v1/messages \
     --header "x-api-key: $ANTHROPIC_API_KEY" \
     --header "anthropic-version: 2023-06-01" \
     --header "content-type: application/json" \
     --data \
'{
    "model": "claude-3-5-sonnet-20240620",
    "max_tokens": 1024,
    "tools": [{
        "name": "get_weather",
        "description": "Get the current weather in a given location",
        "input_schema": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "The city and state, e.g. San Francisco, CA"
                },
                "unit": {
                    "type": "string",
                    "enum": ["celsius", "fahrenheit"],
                    "description": "The unit of temperature, either 'celsius' or 'fahrenheit'"
                }
            },
            "required": ["location"]
        }
    },
    {
        "name": "get_time",
        "description": "Get the current time in a given time zone",
        "input_schema": {
            "type": "object",
            "properties": {
                "timezone": {
                    "type": "string",
                    "description": "The IANA time zone name, e.g. America/Los_Angeles"
                }
            },
            "required": ["timezone"]
        }
    }],
    "messages": [{
        "role": "user",
        "content": "What is the weather like right now in New York? Also what time is it there?"
    }]
}'
```

In this case, Claude will most likely try to use two separate tools, one at a time — `get_weather` and then `get_time` — in order to fully answer the user’s question. However, it will also occasionally output two `tool_use` blocks at once, particularly if they are not dependent on each other. You would need to execute each tool and return their results in separate `tool_result` blocks within a single `user` message.

Missing information

If the user’s prompt doesn’t include enough information to fill all the required parameters for a tool, Claude 3 Opus is much more likely to recognize that a parameter is missing and ask for it. Claude 3 Sonnet may ask, especially when prompted to think before outputting a tool request. But it may also do its best to infer a reasonable value.

For example, using the `get_weather` tool above, if you ask Claude “What’s the weather?” without specifying a location, Claude, particularly Claude 3 Sonnet, may make a guess about tools inputs:

JSON

Copy

```JSON
{
  "type": "tool_use",
  "id": "toolu_01A09q90qw90lq917835lq9",
  "name": "get_weather", 
  "input": {"location": "New York, NY", "unit": "fahrenheit"}
}
```

This behavior is not guaranteed, especially for more ambiguous prompts and for models less intelligent than Claude 3 Opus. If Claude 3 Opus doesn’t have enough context to fill in the required parameters, it is far more likely respond with a clarifying question instead of making a tool call.

Sequential tools

Some tasks may require calling multiple tools in sequence, using the output of one tool as the input to another. In such a case, Claude will call one tool at a time. If prompted to call the tools all at once, Claude is likely to guess parameters for tools further downstream if they are dependent on tool results for tools further upstream.

Here’s an example of using a `get_location` tool to get the user’s location, then passing that location to the `get_weather` tool:

Shell

Python

Copy

```bash
curl https://api.anthropic.com/v1/messages \
     --header "x-api-key: $ANTHROPIC_API_KEY" \
     --header "anthropic-version: 2023-06-01" \
     --header "content-type: application/json" \
     --data \
'{
    "model": "claude-3-5-sonnet-20240620",
    "max_tokens": 1024,
    "tools": [
        {
            "name": "get_location",
            "description": "Get the current user location based on their IP address. This tool has no parameters or arguments.",
            "input_schema": {
                "type": "object",
                "properties": {}
            }
        },
        {
            "name": "get_weather",
            "description": "Get the current weather in a given location",
            "input_schema": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city and state, e.g. San Francisco, CA"
                    },
                    "unit": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "description": "The unit of temperature, either 'celsius' or 'fahrenheit'"
                    }
                },
                "required": ["location"]
            }
        }
    ],
    "messages": [{
        "role": "user",
        "content": "What is the weather like where I am?"
    }]
}'
```

In this case, Claude would first call the `get_location` tool to get the user’s location. After you return the location in a `tool_result`, Claude would then call `get_weather` with that location to get the final answer.

The full conversation might look like:

| Role | Content |
| --- | --- |
| User | What’s the weather like where I am? |
| Assistant | <thinking>To answer this, I first need to determine the user’s location using the get\_location tool. Then I can pass that location to the get\_weather tool to find the current weather there.</thinking>\[Tool use for get\_location\] |
| User | \[Tool result for get\_location with matching id and result of San Francisco, CA\] |
| Assistant | \[Tool use for get\_weather with the following input\]{ “location”: “San Francisco, CA”, “unit”: “fahrenheit” } |
| User | \[Tool result for get\_weather with matching id and result of “59°F (15°C), mostly cloudy”\] |
| Assistant | Based on your current location in San Francisco, CA, the weather right now is 59°F (15°C) and mostly cloudy. It’s a fairly cool and overcast day in the city. You may want to bring a light jacket if you’re heading outside. |

This example demonstrates how Claude can chain together multiple tool calls to answer a question that requires gathering data from different sources. The key steps are:

1. Claude first realizes it needs the user’s location to answer the weather question, so it calls the `get_location` tool.
2. The user (i.e. the client code) executes the actual `get_location` function and returns the result “San Francisco, CA” in a `tool_result` block.
3. With the location now known, Claude proceeds to call the `get_weather` tool, passing in “San Francisco, CA” as the `location` parameter (as well as a guessed `unit` parameter, as `unit` is not a required parameter).
4. The user again executes the actual `get_weather` function with the provided arguments and returns the weather data in another `tool_result` block.
5. Finally, Claude incorporates the weather data into a natural language response to the original question.

Chain of thought tool use

By default, Claude 3 Opus is prompted to think before it answers a tool use query to best determine whether a tool is necessary, which tool to use, and the appropriate parameters. Claude 3 Sonnet and Claude 3 Haiku are prompted to try to use tools as much as possible and are more likely to call an unnecessary tool or infer missing parameters. To prompt Sonnet or Haiku to better assess the user query before making tool calls, the following prompt can be used:

Chain of thought prompt

`Answer the user's request using relevant tools (if they are available). Before calling a tool, do some analysis within \<thinking>\</thinking> tags. First, think about which of the provided tools is the relevant tool to answer the user's request. Second, go through each of the required parameters of the relevant tool and determine if the user has directly provided or given enough information to infer a value. When deciding if the parameter can be inferred, carefully consider all the context to see if it supports a specific value. If all of the required parameters are present or can be reasonably inferred, close the thinking tag and proceed with the tool call. BUT, if one of the values for a required parameter is missing, DO NOT invoke the function (not even with fillers for the missing params) and instead, ask the user to provide the missing parameters. DO NOT ask for more information on optional parameters if it is not provided.`

JSON mode

You can use tools to get Claude produce JSON output that follows a schema, even if you don’t have any intention of running that output through a tool or function.

When using tools in this way:

- You usually want to provide a **single** tool
- You should set `tool_choice` (see [Forcing tool use](https://docs.anthropic.com/en/docs/tool-use#forcing-tool-use)) to instruct the model to explicitly use that tool
- Remember that the model will pass the `input` to the tool, so the name of the tool and description should be from the model’s perspective.

The following uses a `record_summary` tool to describe an image following a particular format.

Shell

Python

Copy

```bash
#!/bin/bash
IMAGE_URL="https://upload.wikimedia.org/wikipedia/commons/a/a7/Camponotus_flavomarginatus_ant.jpg"
IMAGE_MEDIA_TYPE="image/jpeg"
IMAGE_BASE64=$(curl "$IMAGE_URL" | base64)

curl https://api.anthropic.com/v1/messages \
     --header "content-type: application/json" \
     --header "x-api-key: $ANTHROPIC_API_KEY" \
     --header "anthropic-version: 2023-06-01" \
     --data \
'{
    "model": "claude-3-sonnet-20240229",
    "max_tokens": 1024,
    "tools": [{
        "name": "record_summary",
        "description": "Record summary of an image using well-structured JSON.",
        "input_schema": {
            "type": "object",
            "properties": {
                "key_colors": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "r": { "type": "number", "description": "red value [0.0, 1.0]" },
                            "g": { "type": "number", "description": "green value [0.0, 1.0]" },
                            "b": { "type": "number", "description": "blue value [0.0, 1.0]" },
                            "name": { "type": "string", "description": "Human-readable color name in snake_case, e.g. \"olive_green\" or \"turquoise\"" }
                        },
                        "required": [ "r", "g", "b", "name" ]
                    },
                    "description": "Key colors in the image. Limit to less then four."
                },
                "description": {
                    "type": "string",
                    "description": "Image description. One to two sentences max."
                },
                "estimated_year": {
                    "type": "integer",
                    "description": "Estimated year that the images was taken, if is it a photo. Only set this if the image appears to be non-fictional. Rough estimates are okay!"
                }
            },
            "required": [ "key_colors", "description" ]
        }
    }],
    "tool_choice": {"type": "tool", "name": "record_summary"},
    "messages": [
        {"role": "user", "content": [
            {"type": "image", "source": {
                "type": "base64",
                "media_type": "'$IMAGE_MEDIA_TYPE'",
                "data": "'$IMAGE_BASE64'"
            }},
            {"type": "text", "text": "Describe this image."}
        ]}
    ]
}'
```

---

## 

[​

](https://docs.anthropic.com/en/docs/build-with-claude/tool-use#pricing)

Pricing

Tool use requests are priced the same as any other Claude API request, based on the total number of input tokens sent to the model (including in the `tools` parameter) and the number of output tokens generated.”

The additional tokens from tool use come from:

- The `tools` parameter in API requests (tool names, descriptions, and schemas)
- `tool_use` content blocks in API requests and responses
- `tool_result` content blocks in API requests

When you use `tools`, we also automatically include a special system prompt for the model which enables tool use. The number of tool use tokens required for each model are listed below (excluding the additional tokens listed above):

| Model | Tool choice | Tool use system prompt token count |
| --- | --- | --- |
| Claude 3.5 Sonnet | `auto`
---

`any`, `tool` | 294 tokens

---

261 tokens |
| Claude 3 Opus | `auto`

---

`any`, `tool` | 530 tokens

---

281 tokens |
| Claude 3 Sonnet | `auto`

---

`any`, `tool` | 159 tokens

---

235 tokens |
| Claude 3 Haiku | `auto`

---

`any`, `tool` | 264 tokens

---

340 tokens |

These token counts are added to your normal input and output tokens to calculate the total cost of a request. Refer to our [models overview table](https://docs.anthropic.com/en/docs/models-overview#model-comparison) for current per-model prices.

When you send a tool use prompt, just like any other API request, the response will output both input and output token counts as part of the reported `usage` metrics.





