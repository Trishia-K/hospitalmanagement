# Hospital Management System 

**KOBUMANZI TRISHIA**  
**M24B23/011**   
**BSCS** 

## Project description

This is an open-source Hospital Management System built with Python and Django.
It allows hospitals to manage doctors, patients, and appointments through a website.

Original project by: sumitkumar1503  
Original link: https://github.com/sumitkumar1503/hospitalmanagement


## What did I do?

I forked this project then I ran it on my computer and then analyzed and improved how it handles errors.
The original code had many places where things could go wrong and the app would simply crash with no explanation. I fixed these problems and added logging so that errors are recorded properly.

### 1 — Analyze poorly written error handling code
I looked through the main file `hospital/views.py` and found 7 problems:

1. The app crashed if you tried to delete a doctor or patient that didn't exist
2. The app crashed if billing form fields were empty or had wrong values
3. The PDF bill download crashed if no discharge record existed
4. The PDF generator returned nothing when it failed, with no message
5. The contact form crashed if the email server had a problem
6. Search boxes crashed if someone submitted an empty search
7. There was zero logging anywhere in the entire file

### 2 — Improve exception strategies with targeted fixes
I rewrote the broken parts using try/except blocks for example in the views file, the delete_doctor_from_hospitl_view function crashes the program if a doctor does not exist but I fixed it by adding a block ObjectDoesNotExist so that it can just show an error.

### 3 — Add meaningful logging
I added logging at the top of `views.py` so that all errors and actions are recorded in `hospital_debug.log` so developers can see what happened. 
I also added log messages throughout the code:
- `logger.info(...)` — when something works correctly
- `logger.warning(...)` — when something unusual happens
- `logger.error(...)` — when something goes wrong


### 4 — Compare AI vs human reasoning
- For most errors I used simple if-checks, but AI suggested using specific exception types like ObjectDoesNotExist and ValueError which handle the problems better.
- For the contact form error message, I used a clearer message explaining exactly what went wrong but AI had just suggested a generic 'please try again' message which is not very helpful to the user.
