# Common Code Smells

## Long Function
- Symptom: one function mixes fetching, validation, transformation, and output
- Typical fix: extract focused helpers

## Duplication
- Symptom: same logic appears in several places with tiny variations
- Typical fix: extract shared function or shared object

## Large Module / God Object
- Symptom: one file owns unrelated responsibilities
- Typical fix: split by responsibility and interface

## Long Parameter List
- Symptom: function signature is hard to read or call correctly
- Typical fix: parameter object or builder

## Nested Conditionals
- Symptom: arrow code, deep indentation
- Typical fix: guard clauses or smaller decision helpers

## Magic Values
- Symptom: unexplained numbers or strings drive behavior
- Typical fix: named constants or domain types
