# Copilot Instructions

## Hard rules (must follow)
- DO NOT refactor unrelated code
- DO NOT config values
- DO NOT add inline loops or conditionals. Always use full statements.

## Coding rules
- Prefer existing patterns in the codebase
- Keep changes minimal and localized
- If uncertain, ask before changing behavior

## Style
- No emojis
- No explanations unless requested

# Coding Conventions (MANDATORY)

## Python
- Use snake_case for all variables, functions, and methods
- Use PascalCase for class names
- Follow PEP 8 strictly

## Database
- Use snake_case for all table names and columns

## API (HTTP / JSON)
- Use camelCase for all request and response fields
- Never expose snake_case fields in API responses

## Mapping Rules
- Backend internals (Python, DB) MUST remain snake_case
- API boundaries MUST convert snake_case → camelCase
- Use explicit mapping or schema aliasing (e.g. Pydantic aliases)

Any generated code that violates these rules is incorrect.
