# from datetime import datetime
# from transformers import pipeline
# import torch

# # Determine the best device for macOS
# if torch.backends.mps.is_available():
#     device = "mps"  # Apple Silicon GPU acceleration
# elif torch.cuda.is_available():
#     device = "cuda"  # NVIDIA GPU (not available on macOS)
# else:
#     device = "cpu"  # CPU fallback

# pipe = pipeline(
#     "text-generation",
#     model="google/gemma-3-1b-it",
#     device=device,
#     torch_dtype=torch.bfloat16,
# )
# def extract_transaction_details(email_message_list: list[str]) -> str:

#     final_message = "\n\n" + "\n\n".join(email_message_list)
#     messages = [
#         {
#             "role": "system",
#             "content": [{"type": "text", "text": """You are an expert data extraction assistant specialized in financial transaction alert messages from banks, credit cards, or UPI platforms.

#         **Your Goal:** Extract the specified data fields from the provided message(s) and return **ONLY** a valid JSON list. Each item in the list must be a JSON object representing one transaction.

#         **Strict Output Requirements:**
#         * **Absolutely no conversational text, explanations, or markdown formatting (e.g., ```json) outside the JSON list itself.**
#         * The response must begin with `[` and end with `]`.

#         **Extracted Fields and Constraints:**
#         * `id` (string): Unique identifier for the message. This maps to the "ID" in the message.
#         * `amount` (number): Numeric value of the transaction. Do not include currency symbols.
#         * `transaction_type` (string): **Strictly** one of: "debit" or "credit".
#         * `source_identifier` (string): Account number, card number, or UPI ID from which money was deducted or into which money was received.
#         * `destination` (string): Name, UPI ID, merchant, or platform that is the recipient or sender.
#         * `reference_number` (string): UPI or bank transaction reference number. Can be an empty string if not found.
#         * `mode` (string): **Strictly** one of: "UPI", "Credit Card", "Bank Transfer", "ATM", "POS", or "Unknown".
#         * `reason` (string): Description or reason for the transaction. Can be an empty string if not found.
#         * `date` (string): The transaction date in 'YYYY-MM-DD' format. If the year is not explicitly mentioned, assume the current year (2025). If the date is not found, return `null`.

#         Rules:
#         1. Exclude any emails that is for OTPs, promotional offers, or non-transactional alerts.
#         2. Return an empty JSON list `[]` if no valid transactions are found.
#         3. A transaction must have at least amount, transaction_type, source_identifier, and destination to be considered valid.

#         **Example Message and Expected Output:**

#         Message: "Dear Customer, Rs.65.00 has been debited from account 1531 to VPA Q285361434@ybl MADHU SUDHAN S on 04-07-25. Your UPI transaction reference number is 254342617978. Thread-ID: 1234567890abcdef"

#         Expected Output:
#         ```json
#         [
#             {
#                 "id": "1234567890abcdef",
#                 "amount": 65.00,
#                 "transaction_type": "debit",
#                 "source_identifier": "1531",
#                 "destination": "Q285361434@ybl MADHU SUDHAN S",
#                 "reference_number": "254342617978",
#                 "mode": "UPI",
#                 "reason": "Payment to VPA Q285361434@ybl MADHU SUDHAN S",
#                 "date": "2025-07-04"
#             }
#         ]
        
#         Example 2:
#         Message: "Freshworks Lead Software Engineer - Backend: Organizations everywhere struggle under the weight of their data. They need a solution that can help them manage and analyze their data effectively."

#         Expected Output:
#         ```json
#         []
#         ```
#         """}]
#         },
#         {
#             "role": "user",
#             "content": [
#                 {"type": "text", "text": "What is the transaction details in the following email message?"},
#                 {"type": "text", "text": final_message}
#             ]
#         }
#     ]
#     start_time = datetime.now()
#     output = pipe(text_inputs=messages, max_new_tokens=2000)
#     end_time = datetime.now()
#     print(f"Processing time: {(end_time - start_time).total_seconds()}")
#     return output[0]["generated_text"][-1]["content"]