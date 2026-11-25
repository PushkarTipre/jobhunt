# Form profile (details the apply assistant may type into company-site application forms)

PRIVATE FILE. Never commit your filled-in copy. Only fields with `fill: yes` may be typed into a form. Anything not listed, `fill: no`, or `TO_BE_CONFIRMED` makes the assistant stop and leave the job for you.

The assistant NEVER enters: government ID numbers, bank or card details, passwords, OTPs.

## Identity and contact
- full_name: <name>                 fill: yes
- first_name: <first>               fill: yes
- last_name: <last>                 fill: yes
- email: <email>                    fill: yes
- phone_with_code: <+91XXXXXXXXXX>  fill: yes
- phone_10_digit: <XXXXXXXXXX>      fill: yes
- linkedin: <url>                   fill: yes
- github: <url>                     fill: yes
- portfolio: <url>                  fill: yes

## Location
- current_city: <city>              fill: yes
- current_state: <state>            fill: yes
- country: <country>                fill: yes
- nationality: <nationality>        fill: yes
- work_authorization: <text>        fill: yes
- full_address: <address>           fill: no
- pincode: <pincode>                fill: yes
- date_of_birth: <DD/MM/YYYY>       fill: no

## Current job
- current_employer: <employer>      fill: yes
- current_title: <title>            fill: yes
- employed_since: <Mon YYYY>        fill: yes
- notice_period: <text>             fill: yes
- current_ctc_lpa: <n>              fill: yes
- expected_ctc_range: <range>       fill: yes
- expected_ctc_single: <n>          fill: yes
- reason_for_leaving: TO_BE_CONFIRMED   fill: no

## Education
- degree: <degree>                  fill: yes
- university: <university>          fill: yes
- years: <YYYY to YYYY>             fill: yes

## Optional text (the assistant may paste ONLY this exact text into a free-text box)
- cover_note: <your own short note>   fill: no

## Sensitive and equal-opportunity questions
Never filled by the assistant.
