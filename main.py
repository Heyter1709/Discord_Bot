import discord
from discord.ext import commands
import random
import openai
import asyncio
from gtts import gTTS
import time
import os
import json
from base64 import b64decode
import re



openai.api_key = "API"
model_engine = "text-davinci-003"


intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

role_ids = ["MODERS_ROLES"]

conversation_history = {}

async def generate_response(question, speaker=None, topic=None):
    prompt = f"Q: {question}"
    if speaker:
        prompt += f"\nS: {speaker}"
    if topic:
        prompt += f"\nT: {topic}"
    prompt += "\nA:"
    response = openai.Completion.create(
        engine=model_engine,
        prompt=prompt,
        max_tokens=2048,
        n=1,
        stop=None,
        temperature=0,
    )
    answer = response.choices[0].text.strip()
    return answer

@bot.command()
async def ask(ctx):
    await ctx.send("Ожидайте...")
    question = ctx.message.content.strip()
    if question in conversation_history:
        answer = conversation_history[question]["answer"]
    else:
        answer = await generate_response(question)
        conversation_history[question] = {"answer": answer, "follow_up": {}}

    response = f"```\n{answer}\n```"

    while True:
        message = await ctx.send(response)
        await message.add_reaction('➕')
        def check(reaction, user):
            return user == ctx.message.author and str(reaction.emoji) == '➕' and reaction.message.id == message.id

        try:
            reaction, user = await bot.wait_for('reaction_add', timeout=60.0, check=check)
        except asyncio.TimeoutError:
            await message.clear_reaction('➕')
            break
        else:
            await message.clear_reaction('➕')
            await ctx.send("Введите дополнительный вопрос:")
            try:
                new_question = await bot.wait_for('message', timeout=60.0, check=lambda m: m.author == ctx.author and m.channel == ctx.channel)
            except asyncio.TimeoutError:
                await ctx.send("Превышено время ожидания.")
            else:
                new_answer = await generate_response(new_question.content.strip(), speaker=None, topic=question)
                if question in conversation_history:
                    conversation_history[question]["follow_up"][new_question.content.strip()] = new_answer
                else:
                    conversation_history[question] = {"answer": answer, "follow_up": {new_question.content.strip(): new_answer}}
                response = f"```\n{format_conversation_history(conversation_history[question])}\n```"


def format_conversation_history(conversation_history):
    formatted_history = f"Бот: {conversation_history['answer']}\n"
    for i, (follow_up_question, follow_up_answer) in enumerate(conversation_history['follow_up'].items()):
        formatted_history += f"\nТы-{i + 1}: {follow_up_question}\nБот-{i + 1}: {follow_up_answer}"

    return formatted_history

@bot.command()
async def rand(ctx,*,question):
    answers = ['Да', 'Нет', 'Больше да чем нет', 'Скорее нет', 'Иди умойся чушка ебаная и не пиши мне больше!']
    response = random.choice(answers)
    embed = discord.Embed(title='Вопрос:', description=question, color=0x00ff00)
    embed.add_field(name='Ответ:', value=response, inline=False)
    await ctx.send(embed=embed)


@bot.command()
async def com(ctx):
    text = """
    Список команд:

    **!rand** - Да или Нет.

    **!ask** - Задайте любой вопрос боту.

    **!remuve** - снимает все роли (доступна только высшей администрации)

    **!add_role** - <id>-человека <id>-роли (доступна только высшей администрации)
    
    **!voice** + "Ваш текст" - переделывает текст в речь(файл mp3).
    
    **!image** + "Ваш текст" - генерирует картинку.(Лучше писать на ангийском!). **Непристойные вещи он вам не выдаст! :monkey:**
    
    **!check** + @"Ваш ник" - Проверить колличество нарушений.
    
    **!warn** + @"Ник нарушителя" + "причина" - Дать варн (Доступно только высшей администрации).
    
    **!unwarn** + @"Ник нарушителя" +"Число" - Снять варн (Доступно только высшей администрации).
    
    """

    # создаем embed и добавляем в него текст
    embed = discord.Embed(title="Команды Поркшеяна", description=text, color=0x00ff00)

    # отправляем embed в чат
    await ctx.send(embed=embed)


@bot.command()
@commands.has_any_role(*role_ids)
async def remove(ctx, member_id: int):
    guild = ctx.guild
    member = guild.get_member(member_id)
    roles_to_remove = [role for role in member.roles if role.name != "@everyone"]
    await member.remove_roles(*roles_to_remove)
    await ctx.send(f"Роли сняты {member.display_name}.")


@bot.command()
@commands.has_any_role(*role_ids)
async def add_role(ctx, user_id: int, role_id: int):
    user = await bot.fetch_user(user_id)
    role = ctx.guild.get_role(role_id)
    await ctx.guild.get_member(user_id).add_roles(role, reason="Роль добавлена!")
    await ctx.send(f"Роль добавлена {role.name} юзеру {user.mention}.")

@bot.command()
async def voice(ctx, *, text):
    await ctx.message.delete()

    file_path = text_to_speech(text)
    with open(file_path, 'rb') as fp:
        voice_message = discord.File(fp, filename='voice_message.mp3')
        await ctx.send(file=voice_message)
    os.remove(file_path)

def text_to_speech(text="TEXT", lang='ru', voice='ru'):
    tts = gTTS(text=text, lang=lang, slow=False, tld='com', lang_check=True, pre_processor_funcs=[])
    unix_time = int(time.time())
    file_path = f'{unix_time}.mp3'
    tts.save(file_path)
    return file_path


@bot.command()
async def image(ctx, *, prompt):
    size_options = ["256x256", "512x512", "1024x1024"]
    size_reactions = ['1️⃣', '2️⃣', '3️⃣']
    size_message = "Выберите размер изображения:\n"
    for i, option in enumerate(size_options):
        size_message += f"{size_reactions[i]} - {option}\n"
    sent_message = await ctx.send(size_message)

    for reaction in size_reactions[:len(size_options)]:
        await sent_message.add_reaction(reaction)

    def check(reaction, user):
        return (
            user == ctx.author
            and reaction.message.id == sent_message.id
            and str(reaction.emoji) in size_reactions[:len(size_options)]
        )

    try:
        reaction, _ = await bot.wait_for(
            "reaction_add", timeout=60.0, check=check
        )
        chosen_size = size_options[size_reactions.index(str(reaction.emoji))]
    except TimeoutError:
        await ctx.send("Время ожидания истекло. Попробуйте снова.")
        return

    response = openai.Image.create(
        prompt=prompt,
        n=1,
        size=chosen_size,
        response_format="b64_json"
    )

    with open("data.json", "w") as file:
        json.dump(response, file, indent=4, ensure_ascii=False)

    image_data = b64decode(response['data'][0]['b64_json'])
    file_name = "_".join(prompt.split(' '))

    with open(f'{file_name}.png', "wb") as file:
        file.write(image_data)

    await ctx.send(file=discord.File(f'{file_name}.png'))

    # Удаление файла
    os.remove(f'{file_name}.png')
    os.remove("data.json")

# Загрузка данных из JSON-файла
def load_data():
    try:
        with open('base.json', 'r') as file:
            data = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}
    return data

# Сохранение данных в JSON-файл
def save_data(data):
    with open('base.json', 'w') as file:
        json.dump(data, file, indent=4)

# Загрузка данных о банах из JSON-файла
def load_bans():
    try:
        with open('base.json', 'r') as file:
            bans = json.load(file).get('bans', {})
    except (FileNotFoundError, KeyError):
        bans = {}
    return bans

# Сохранение данных о банах в JSON-файл
def save_bans(bans):
    data = load_data()
    data['bans'] = bans
    save_data(data)

# Добавление бана пользователю
def add_ban(user_id):
    data = load_data()
    if str(user_id) in data:
        data[str(user_id)]['bans'] += 1
    else:
        data[str(user_id)] = {
            'warns': 0,
            'caps_count': 0,
            'links_count': 0,
            'bans': 1
        }
    save_data(data)


# Сохранение информации о пользователе в файл
def save_user_data(user_id, user_data):
    data = load_data()
    data[str(user_id)] = user_data
    save_data(data)

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Проверка на использование большого количества заглавных букв
    caps_count = sum(1 for c in message.content if c.isupper())
    if caps_count > 5:
        data = load_data()
        member = message.author
        if str(member.id) not in data:
            data[str(member.id)] = {
                'warns': 0,
                'caps_count': 0,
                'links_count': 0,
                'bans': 0
            }
        data[str(member.id)]['caps_count'] += 1
        if data[str(member.id)]['caps_count'] >= 7:
            data[str(member.id)]['warns'] += 1
            data[str(member.id)]['caps_count'] = 0
        if data[str(member.id)]['warns'] >= 7:
            await member.ban(reason='Exceeded the maximum number of warns')
            add_ban(member.id)
            data[str(member.id)]['warns'] = 0
            data[str(member.id)]['caps_count'] = 0
            data[str(member.id)]['links_count'] = 0
        save_user_data(member.id, data[str(member.id)])
        caps_remaining = 7 - data[str(member.id)]['caps_count']
        await message.channel.send(f'{member.mention}, Осталось предупреждений до мута: {caps_remaining}/7.')

    # Проверка на использование ссылок
    link_regex = re.compile(r'(https?://\S+)')
    if link_regex.search(message.content):
        data = load_data()
        member = message.author
        if str(member.id) not in data:
            data[str(member.id)] = {
                'warns': 0,
                'caps_count': 0,
                'links_count': 0,
                'bans': 0
            }
        data[str(member.id)]['links_count'] += 1
        if data[str(member.id)]['links_count'] >= 5:
            data[str(member.id)]['warns'] += 1
            data[str(member.id)]['links_count'] = 0
        if data[str(member.id)]['warns'] >= 7:
            await member.ban(reason='Exceeded the maximum number of warns')
            add_ban(member.id)  # Добавляем бан
            data[str(member.id)]['warns'] = 0
            data[str(member.id)]['caps_count'] = 0
            data[str(member.id)]['links_count'] = 0
        save_user_data(member.id, data[str(member.id)])
        links_remaining = 5 - data[str(member.id)]['links_count']
        await message.channel.send(
            f'{member.mention}, Осталось предупреждений за использование ссылок: {links_remaining}/5.')
        if data[str(member.id)]['warns'] >= 7:
            await message.channel.send(
                f'{member.mention}, превысил максимальное количество предупреждений и был забанен.')
            await member.ban(reason='Exceeded the maximum number of warns')
            add_ban(member.id)

    await bot.process_commands(message)

@bot.command()
@commands.has_any_role(*role_ids)
async def warn(ctx, member: discord.Member, *, reason=None):
    data = load_data()
    if str(member.id) not in data:
        data[str(member.id)] = {
            'warns': 0,
            'caps_count': 0,
            'links_count': 0,
            'bans': 0
        }
    data[str(member.id)]['warns'] += 1
    save_user_data(member.id, data[str(member.id)])
    if reason ==None:
        await ctx.send(f'{member.mention} получил предупреждение. Причина: отсутствует')
    else:
        await ctx.send(f'{member.mention} получил предупреждение. Причина: {reason}')

    if data[str(member.id)]['warns'] >= 7:
        data[str(member.id)]['warns'] = 0
        data[str(member.id)]['caps_count'] = 0
        data[str(member.id)]['links_count'] = 0
        data[str(member.id)]['bans'] += 1
        await member.ban(reason='Exceeded the maximum number of warns')
        add_ban(member.id)

@bot.command()
async def check(ctx, member: discord.Member):
    data = load_data()
    if str(member.id) not in data:
        await ctx.send('Пользователь не найден в базе данных.')
        return
    warns = data[str(member.id)]['warns']
    caps_count = data[str(member.id)]['caps_count']
    links_count = data[str(member.id)]['links_count']
    ban_count = data[str(member.id)]['bans']
    embed = discord.Embed(title='Проверка пользователя', color=discord.Color.dark_red())
    embed.add_field(name='Имя', value=member.mention, inline=False)
    embed.add_field(name='ID', value=member.id, inline=False)
    embed.add_field(name='Варны', value=f'{warns}/7', inline=False)
    embed.add_field(name='Количество капс нарушений', value=f'{caps_count}/7', inline=False)
    embed.add_field(name='Количество нарушений ссылок', value=f'{links_count}/5', inline=False)
    embed.add_field(name='Количество банов', value=ban_count, inline=False)
    await ctx.send(embed=embed)

@bot.command()
@commands.has_any_role(*role_ids)
async def unwarn(ctx, member: discord.Member,reason=None):
    data = load_data()
    if str(member.id) not in data:
        await ctx.send('Пользователь не найден в базе данных.')
        return
    if reason==None or reason.isdigit()==False:
        await ctx.send("Введите количество варнов для снятия")
    elif reason.isdigit()==True:
        if data[str(member.id)]["warns"] == 0:
            await ctx.send(f'У пользователя {member.mention} нет варнов для снятия')
        elif int(reason) >= data[str(member.id)]["warns"]:
            data[str(member.id)]["warns"] = 0
            await ctx.send(f'У пользователя {member.mention} были сняты все варны')
        elif int(reason)<data[str(member.id)]["warns"]:
            data[str(member.id)]["warns"] -= int(reason)
            await ctx.send(f'У пользователя {member.mention} было снято количество варнов - {reason}')

    save_user_data(member.id, data[str(member.id)])

bot.run('TOKEN')
