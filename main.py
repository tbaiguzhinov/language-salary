import math
import os
from itertools import count

import requests
from dotenv import load_dotenv
from terminaltables import AsciiTable


def predict_salary(salary_from, salary_to):
    """Calculate average salary.

    Accepts:
        salary_from (float): Bottom line salary
        salary_to (float): Top level salary
    Returns:
        (float) Average if both values are provided
        Adds 20% if top level is not given
        Extracts 20% of bottom line is not given
        Rerurns None if both salaries are Null.
    """
    if salary_from and salary_to:
        return (salary_to + salary_from) / 2
    elif not salary_to:
        return salary_from * 1.2
    elif not salary_from:
        return salary_to * 0.8


def predict_rub_salary_for_hh(vacancy):
    """Calculate expected HH salary.

    Accepts:
       vacancy (dict): All information about vacancy from HH.
    Returns:
       (float): Expected salary or None if no salary or not RUR currency.
    """
    if vacancy["salary"] and vacancy["salary"]["currency"] == "RUR":
        return predict_salary(
            vacancy["salary"]["from"],
            vacancy["salary"]["to"]
        )


def predict_rub_salary_for_sj(vacancy):
    """Calculate expected SJ salary.

    Accepts:
       vacancy (dict): All information about vacancy from SJ.
    Returns:
       (float): Expected salary or None if no salary or not RUR currency.
    """
    if vacancy["currency"] == "rub":
        return predict_salary(
            vacancy["payment_from"],
            vacancy["payment_to"]
        )


def get_vacancies_from_hh(language):
    """Gather vacancies from HH for a programming language.

    Function to gather all pages from HH on a specified programming language.
    Accepts:
        language (str): Name of programming language.
    Returns:
        gathered_vacancies (list): Vacancies gathered from all pages.
    """
    programmer_specialization_code = 1.221
    period_days = 30
    moscow_area_code = 1
    gathered_vacancies = []
    for page in count(0):
        params = {
            "specialization": programmer_specialization_code,
            "area": moscow_area_code,
            "period": period_days,
            "text": f"Программист {language}",
            "page": page,
        }
        response = requests.get(
            url="https://api.hh.ru/vacancies",
            params=params,
        )
        response.raise_for_status()
        page_data = response.json()
        gathered_vacancies.extend(page_data["items"])
        if page >= page_data["pages"]-1:
            break
    return gathered_vacancies


def sj_authorization(sj_key, sj_login, sj_app_id, sj_password):
    """Authorize into SuperJob API.

    Accepts:
       sj_key (str): SuperJob API app secret key.
       sj_login (str): SuperJob email address.
       sj_app_id (str): SuperJob API app ID.
       sj_password (str): SuperJob password.
    Returns:
       response.json() (dict): Requests response
    """
    params = {
        "login": sj_login,
        "password": sj_password,
        "client_id": sj_app_id,
        "client_secret": sj_key,
    }
    response = requests.get(
        url="https://api.superjob.ru/2.0/oauth2/password/",
        params=params,
    )
    response.raise_for_status()
    return response.json()


def get_sj_vacancies(language, sj_key, token):
    """Gather vacancies from SJ for a programming language.

    Function to gather all pages from SJ on a specified programming language.
    Accepts:
        language (str): Name of programming language.
        sj_key (str): SuperJob API app secret key.
        token (str): Authorization token for SuperJob.
    Returns:
        gathered_vacancies (list): Vacancies gathered from all pages.
    """
    programming_field_id = 48
    moscow_city_id = 4
    max_number_vacancies_per_page = 100
    gathered_vacancies = []
    for page in count(0):
        headers = {
            "X-Api-App-Id": sj_key,
            "Authorization": f"Bearer {token}",
        }
        params = {
            "keyword": f"Программист {language}",
            "town": moscow_city_id,
            "catalogues": programming_field_id,
            "page": page,
            "count": max_number_vacancies_per_page,
        }
        response = requests.get(
            url="https://api.superjob.ru/2.0/vacancies/",
            headers=headers,
            params=params,
        )
        response.raise_for_status()
        page_data = response.json()
        gathered_vacancies.extend(page_data["objects"])
        last_page = math.ceil(
            page_data["total"]/max_number_vacancies_per_page
        ) - 1
        if page >= last_page:
            break
    return gathered_vacancies


def get_table(title, salaries_per_language):
    """Draw table."""
    table_data = []
    table_data.append([
        "Язык программирования",
        "Вакансий найдено",
        "Вакансий обработано",
        "Средняя зарплата",
    ])
    for language in salaries_per_language:
        table_data.append([
            language,
            salaries_per_language[language]["vacancies_found"],
            salaries_per_language[language]["vacancies_processed"],
            salaries_per_language[language]["average_salary"],
        ])
    table_instance = AsciiTable(table_data, title)
    return table_instance.table


def main():
    """Main function."""
    load_dotenv()
    sj_key = os.getenv("SUPERJOB_SECRET_KEY")
    sj_login = os.getenv("SUPERJOB_LOGIN")
    sj_app_id = os.getenv("SUPERJOB_APP_ID")
    sj_password = os.getenv("SUPERJOB_PASSWORD")
    access_token_information = sj_authorization(
        sj_key=sj_key,
        sj_login=sj_login,
        sj_app_id=sj_app_id,
        sj_password=sj_password,
    )
    programming_languages = [
        "TypeScript",
        "Swift",
        "Scala",
        "Objective-C",
        "Shell",
        "Go",
        "C",
        "C#",
        "C++",
        "PHP",
        "Ruby",
        "Python",
        "Java",
        "JavaScript",
    ]
    salaries_per_language_in_sj = {}
    for language in programming_languages:
        gathered_sj_vacancies = get_sj_vacancies(
            language=language,
            sj_key=sj_key,
            token=access_token_information["access_token"],
        )
        gathered_salaries = []
        for vacancy in gathered_sj_vacancies:
            expected_salary = predict_rub_salary_for_sj(vacancy)
            gathered_salaries.append(expected_salary) \
                if expected_salary else None
        salaries_per_language_in_sj[language] = {
            "vacancies_found": len(gathered_sj_vacancies),
            "vacancies_processed": len(gathered_salaries),
            "average_salary":
            int(sum(gathered_salaries) / len(gathered_salaries))
                if gathered_salaries else None,
        }
    table_for_sj = get_table(
        title="SuperJob Moscow",
        salaries_per_language=salaries_per_language_in_sj,
    )
    salaries_per_language_in_hh = {}
    for language in programming_languages:
        gathered_vacancies = get_vacancies_from_hh(language)
        gathered_salaries = []
        for vacancy in gathered_vacancies:
            expected_salary = predict_rub_salary_for_hh(vacancy)
            gathered_salaries.append(expected_salary) \
                if expected_salary else None
        salaries_per_language_in_hh[language] = {
            "vacancies_found": len(gathered_vacancies),
            "vacancies_processed": len(gathered_salaries),
            "average_salary":
            int(sum(gathered_salaries) / len(gathered_salaries))
                if gathered_salaries else None,
        }
    table_for_hh = get_table(
        title="HeadHunter Moscow",
        salaries_per_language=salaries_per_language_in_hh,
    )
    print(table_for_sj)
    print(table_for_hh)


if __name__ == "__main__":
    main()
