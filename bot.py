import os
import tempfile
import shutil
import requests
import uuid
import pprint

import telegram
from telegram.ext import Updater, MessageHandler, Filters
from telegram.ext import CallbackContext, CommandHandler
from sympy import symbols, solveset, latex, simplify, diff
from sympy.solvers.inequalities import solve_univariate_inequality

from sympy import S
from sympy.plotting import plot
from sympy.parsing.latex import parse_latex
from sympy.parsing.sympy_parser import parse_expr, standard_transformations, function_exponentiation, \
    implicit_multiplication_application
from sympy.calculus.util import continuous_domain, minimum, maximum


# путь
LATEX_URL = "http://latexpng.mathematicos.com"
AUTH = "9a9b0d0b309449ab8ee8e842aef99b7a"


def help(update, context):
    """
    Обработка команды /help
    """
    chat_id = update.message["chat"]["id"]
    context.bot.send_message(chat_id, 'Это бот для решения уравнений и построения графиков функций.'
                                      ' Для того, чтобы бот правильно работал с графиком, напишите '
                                      'в сообщении боту слово "график" или "graph" и после через пробел '
                                      'напишите функцию. Если хотите, чтобы бот решил уравнение со степенью '
                                      'больше, чем один, указывайте сначала переменную, потом символ ^ , а потом '
                                      'степень. Уравнения пишутся с переменной "x"')


def simplify_cmd(update, context):
    """
    Обработка команды /simplify
    """
    chat_id = update.message["chat"]["id"]
    context.chat_data["cmd"] = "simplify"
    context.bot.send_message(chat_id, "Введите выражение для упрощения в виде x^2+2x+1 "
                                      "(помощь по записи выражений /help_formula)")


def graph(update, context):
    """
    Обработка команды /graph
    """
    chat_id = update.message["chat"]["id"]
    context.chat_data["cmd"] = "graph"
    context.bot.send_message(chat_id, "Введите график функции в виде x^2+2x+1 "
                                      "(помощь по записи выражений /help_formula)")


def solve(update, context):
    """
    Обработка команды /solve
    """
    chat_id = update.message["chat"]["id"]
    context.chat_data["cmd"] = "solve"
    context.bot.send_message(chat_id, "Укажите уравнение или неравенство в виде x^2+2x+1=2 "
                                      "(помощь по записи выражений /help_formula)")


def help_formula(update, context):
    """
    Обработка команды /help_formula
    """
    chat_id = update.message["chat"]["id"]
    context.bot.send_message(chat_id, "График или свойства функции: kx+b или k/x+b kx^2+b,"
                                      " где k - коэффициент наклона и b - "
                             "свободный член;\n\nУравнение: ax^2+bx+c=d или ax+b = c или любой "
                             "другой степени, где a, b, c, d - коэффициенты;\n\n"
                             "Неравенства: ax+b>c или ax+b<ax+c или любой "
                             "степени x, где a, b, c, d - коэффициенты; \n\n"
                             "Упрощение выражения: любая формула.")


def analyze(update, context):
    """
    Обработка /analyze
    """
    chat_id = update.message["chat"]["id"]
    context.chat_data["cmd"] = "analyze"
    context.bot.send_message(chat_id, "Укажите функцию в виде x^2+2x+1 "
                                      "(помощь по записи выражений /help_formula)")

def text(update, context):
    chat_id = update.message["chat"]["id"]

    if context.chat_data.get("cmd") == "graph":
        # Построение графика функции
        clear_context_cmd(context)

        context.bot.send_chat_action(chat_id, telegram.ChatAction.TYPING)
        try:
            expr = parse_user_formula(update.message.text)
        except Exception as e:
            context.bot.send_message(chat_id, f"Не могу понять выражение {update.message.text}: {e} "
                                              f"(помощь по записи выражений /help_formula)")
            return

        x = symbols("x")
        try:
            p1 = plot(expr, (x, -5, 5), show=False)
        except Exception as e:
            context.bot.send_message(chat_id, f"Не могу построить график для {update.message.text}: {e} "
                                              f"(помощь по записи выражений /help_formula)")
            return

        tempfolder = tempfile.mkdtemp()
        os.makedirs(tempfolder, exist_ok=True)

        image_filename = os.path.join(tempfolder, "graf.png")
        p1.save(image_filename)

        with open(image_filename, "rb") as file:
            context.bot.send_photo(chat_id, file)

        shutil.rmtree(tempfolder, ignore_errors=True)

    elif context.chat_data.get("cmd") == "simplify":
        clear_context_cmd(context)
        context.bot.send_chat_action(chat_id, telegram.ChatAction.TYPING)
        try:
            expr = parse_user_formula(update.message.text)
        except Exception as e:
            context.bot.send_message(chat_id, f"Не могу понять выражение {update.message.text}: {e} "
                                              f"(помощь по записи выражений /help_formula)")
            return

        x = symbols("x")

        try:
            solution = latex(simplify(expr))
        except Exception as e:
            context.bot.send_message(chat_id, f"Не могу упростить {update.message.text}: {e} "
                                              f"(помощь по записи выражений /help_formula)")
            return

        image_key = str(uuid.uuid4()).replace("-", "")

        try:
            r = requests.post(url=LATEX_URL,
                              json={"formula": solution, "resolution": 600, "auth": AUTH, "image_key": image_key})

            r.raise_for_status()
        except:
            context.bot.send_message(chat_id, f"Не могу нарисовать картинку с решением {update.message.text}. "
                                              f"Высылаю решение так:")
            context.bot.send_message(chat_id, str(solution))
            return

        tempfolder = tempfile.mkdtemp()
        os.makedirs(tempfolder, exist_ok=True)
        image_filename = os.path.join(tempfolder, "solution.png")
        with open(image_filename, "wb") as file:
            file.write(r.content)

        try:
            with open(image_filename, "rb") as file:
                context.bot.send_photo(chat_id, file)
        except:
            context.bot.send_message(chat_id=chat_id, text=LATEX_URL + "/png/" + image_key)

        finally:
            shutil.rmtree(tempfolder, ignore_errors=True)

    elif context.chat_data.get("cmd") == "analyze":
        clear_context_cmd(context)

        context.bot.send_chat_action(chat_id, telegram.ChatAction.TYPING)
        try:
            expr = parse_user_formula(update.message.text)
        except Exception as e:
            context.bot.send_message(chat_id, f"Не могу понять выражение {update.message.text}: {e} "
                                              f"(помощь по записи выражений /help_formula)")
            return

        x = symbols("x")

        # область определения
        try:
            solution = continuous_domain(expr, x, domain=S.Reals)
        except Exception as e:
            context.bot.send_message(chat_id, f"Не могу найти область определения: {e}")
        else:
            context.bot.send_message(chat_id, "Область определения:")
            send_formula_image_to_telegram(chat_id, context, latex(solution))

        context.bot.send_chat_action(chat_id, telegram.ChatAction.TYPING)

        # Минимальное и макс.значение функции
        try:
            solution = minimum(expr, x, domain=S.Reals)
        except Exception as e:
            context.bot.send_message(chat_id, f"Не могу найти минимальное значение функции: {e}")
        else:
            context.bot.send_message(chat_id, "Минимум функции:")
            send_formula_image_to_telegram(chat_id, context, latex(solution))

        context.bot.send_chat_action(chat_id, telegram.ChatAction.TYPING)

        try:
            solution = maximum(expr, x, domain=S.Reals)
        except Exception as e:
            context.bot.send_message(chat_id, f"Не могу найти максимальное значение функции: {e}")
        else:
            context.bot.send_message(chat_id, "Максимум функции:")
            send_formula_image_to_telegram(chat_id, context, latex(solution))

        context.bot.send_chat_action(chat_id, telegram.ChatAction.TYPING)

        # нули функции
        try:
            solution = solveset(expr, x, domain=S.Reals)
        except Exception as e:
            context.bot.send_message(chat_id, f"Не могу найти нули функции: {e}")
        else:
            context.bot.send_message(chat_id, "Нули функции:")
            send_formula_image_to_telegram(chat_id, context, latex(solution))

        context.bot.send_chat_action(chat_id, telegram.ChatAction.TYPING)

        # периоды знакопостоянства
        try:
            solution = solve_univariate_inequality(expr > 0, x)
        except Exception as e:
            context.bot.send_message(chat_id, f"Не могу найти интервалы функции > 0: {e}")
        else:
            context.bot.send_message(chat_id, "Интервалы, на которых функция больше нуля:")
            send_formula_image_to_telegram(chat_id, context, latex(solution))

        context.bot.send_chat_action(chat_id, telegram.ChatAction.TYPING)

        try:
            solution = solve_univariate_inequality(expr < 0, x)
        except Exception as e:
            context.bot.send_message(chat_id, f"Не могу найти интервалы функции < 0: {e}")
        else:
            context.bot.send_message(chat_id, "Интервалы, на которых функция меньше нуля:")
            send_formula_image_to_telegram(chat_id, context, latex(solution))

        context.bot.send_chat_action(chat_id, telegram.ChatAction.TYPING)

        # периоды монотонности функции
        df = diff(expr)

        try:
            solution = solve_univariate_inequality(df > 0, x)
        except Exception as e:
            context.bot.send_message(chat_id, f"Не могу найти интервалы возрастания: {e}")
        else:
            context.bot.send_message(chat_id, "Интервалы возрастания функции:")
            send_formula_image_to_telegram(chat_id, context, latex(solution))

        context.bot.send_chat_action(chat_id, telegram.ChatAction.TYPING)

        try:
            solution = solve_univariate_inequality(df < 0, x)
        except Exception as e:
            context.bot.send_message(chat_id, f"Не могу найти интервалы убывания функции: {e}")
        else:
            context.bot.send_message(chat_id, "Интервалы убывания функции:")
            send_formula_image_to_telegram(chat_id, context, latex(solution))

    else:
        clear_context_cmd(context)

        context.bot.send_chat_action(chat_id, telegram.ChatAction.TYPING)
        try:
            expr = parse_user_formula(update.message.text)
        except Exception as e:
            context.bot.send_message(chat_id, f"Не могу понять выражение {update.message.text}: {e} "
                                              f"(помощь по записи выражений /help_formula)")
            return

        x = symbols("x")

        if "<" in update.message.text or ">" in update.message.text:
            # это неравенство
            try:
                solution = latex(solve_univariate_inequality(expr, x))
            except Exception as e:
                context.bot.send_message(chat_id, f"Не могу решить {update.message.text}: {e} "
                                                  f"(помощь по записи выражений /help_formula)")
                return
        else:
            # это уравнение
            try:
                solution = latex(solveset(expr, x, domain=S.Reals))
            except Exception as e:
                context.bot.send_message(chat_id, f"Не могу решить {update.message.text}: {e} "
                                                  f"(помощь по записи выражений /help_formula)")
                return

        image_key = str(uuid.uuid4()).replace("-", "")

        try:
            r = requests.post(url=LATEX_URL,
                              json={"formula": solution, "resolution": 600, "auth": AUTH, "image_key": image_key})

            r.raise_for_status()
        except:
            context.bot.send_message(chat_id, f"Не могу нарисовать картинку с решением {update.message.text}. "
                                              f"Высылаю решение так:")
            context.bot.send_message(chat_id, str(solution))
            return

        tempfolder = tempfile.mkdtemp()
        os.makedirs(tempfolder, exist_ok=True)
        image_filename = os.path.join(tempfolder, "solution.png")
        with open(image_filename, "wb") as file:
            file.write(r.content)

        try:
            with open(image_filename, "rb") as file:
                context.bot.send_photo(chat_id, file)
        except:
            context.bot.send_message(chat_id=chat_id, text=LATEX_URL + "/png/" + image_key)

        finally:
            shutil.rmtree(tempfolder, ignore_errors=True)


def parse_user_formula(formula):
    """
    Переводит запись формулы в выражение для sympy
    """
    try:
        # transformations = standard_transformations + (implicit_multiplication_application, function_exponentiation)
        # expr = parse_expr(formula, transformations=transformations, evaluate=False)
        expr = parse_latex(formula)
    except:
        # попробуем распарсить как латех
        raise


    return expr


def clear_context_cmd(context):
    """ """
    if context.chat_data and "cmd" in context.chat_data:
        del context.chat_data["cmd"]


def send_formula_image_to_telegram(chat_id, context, latex_formula):
    """ Отправляет изображение формулы в телеграм """
    image_key = str(uuid.uuid4()).replace("-", "")

    try:
        r = requests.post(url=LATEX_URL,
                          json={"formula": latex_formula, "resolution": 600, "auth": AUTH, "image_key": image_key})

        r.raise_for_status()
    except:
        context.bot.send_message(chat_id, f"Не могу нарисовать картинку с формулой. Высылаю решение так:")
        context.bot.send_message(chat_id, str(latex_formula))
        return

    tempfolder = tempfile.mkdtemp()
    os.makedirs(tempfolder, exist_ok=True)
    image_filename = os.path.join(tempfolder, "solution.png")
    with open(image_filename, "wb") as file:
        file.write(r.content)

    try:
        with open(image_filename, "rb") as file:
            context.bot.send_photo(chat_id, file)
    except:
        context.bot.send_message(chat_id=chat_id, text=LATEX_URL + "/png/" + image_key)

    finally:
        shutil.rmtree(tempfolder, ignore_errors=True)


def main():
    updater = Updater(os.getenv("BOT_TOKEN"), use_context=True)

    dp = updater.dispatcher
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(CommandHandler("start", help))
    dp.add_handler(CommandHandler("solve", solve))
    dp.add_handler(CommandHandler("graph", graph))
    dp.add_handler(CommandHandler("help_formula", help_formula))
    dp.add_handler(CommandHandler("simplify", simplify_cmd))
    dp.add_handler(CommandHandler("analyze", analyze))
    text_handler = MessageHandler(Filters.text, text)
    dp.add_handler(text_handler)

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()


