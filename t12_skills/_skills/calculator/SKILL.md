---
name: calculator
description: Use it for calculating mathematical expressions.
---

# Calculator Skill
This skill users the calulate.py as the calculator, run it with expressions, and give back the results

## Quick Start
The shell command to run the script.
Hint: the script takes an expression as a command-line argument:
  python /skills/calculator/scripts/calculate.py "<expression>"

## Supported Operations
Arithmetic, Power / exponentiation, Square, Floor division and modulo operators, Trigonometric functions, Mathematical constants, Grouping with parentheses

## Supported Functions and constants
Square root (sqrt), absolute value (abs), rounding (round)
Floor and ceiling (floor, ceil)
Natural log and base-10 log (log, log10)
Trigonometric functions: sine, cosine, tangent (sin, cos, tan)
The constants pi (pi) and Euler's number (e)

## Workflow
1. create expression
2. run script with expression
3. return the result only

## Examples
1. exmaple:
./calculate.py "round(3 * 10)"
Expression: round(3 * 10)
Result: 30

Return 30

2. example:
./calculate.py "abs(10 - 3)"
Expression: abs(10 - 3)
Result: 7

Return 7