import os
import random
import requests
from datetime import datetime, timedelta
from io import BytesIO
from decimal import Decimal
from django.utils import timezone

from django.conf import settings
from django.contrib.auth.models import User, Group
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from faker import Faker
from model_bakery import baker
from PIL import Image, ImageDraw, ImageFont
from app_users.models import Avatar, Profile
from catalog.models import (
    Banner,
    Category,
    Product,
    ProductImage,
    Review,
    Sale,
    Specification,
    Tag,
)
from order.models import Order, OrderItem

fake = Faker("ru_RU")


def generate_phone_number():
    """Генерирует телефон в формате только цифр (10 цифр)"""
    return int(f"9{random.randint(100000000, 999999999)}")


def create_category_image(category_name):
    """Создаёт изображение категории с текстом на цветном фоне"""
    colors = {
        "Одежда": (70, 130, 180),
        "Обувь": (139, 69, 19),
        "Электроника": (25, 25, 112),
        "Дом и сад": (34, 139, 34),
        "Красота и здоровье": (255, 105, 180),
        "Спорт и отдых": (255, 140, 0),
        "Игрушки": (255, 20, 147),
        "Книги": (210, 105, 30),
    }
    color = colors.get(category_name, (random.randint(100, 200), random.randint(100, 200), random.randint(100, 200)))
    img = Image.new("RGB", (600, 400), color=color)
    draw = ImageDraw.Draw(img)
    draw.rectangle([10, 10, 590, 390], outline=(255, 255, 255), width=3)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
    except:
        font = ImageFont.load_default()
    text = category_name[:25]
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (600 - text_width) // 2
    y = (400 - text_height) // 2
    draw.text((x, y), text, fill=(255, 255, 255), font=font)
    img_io = BytesIO()
    img.save(img_io, format="PNG", quality=90)
    filename = f"{slugify(category_name)[:30]}_{random.randint(1000, 9999)}.png"
    return ContentFile(img_io.getvalue(), name=filename)


def download_avatar(username, gender=None, index=0):
    """Скачивает случайную аватарку с randomuser.me"""
    if gender is None:
        gender = random.choice(['male', 'female'])
    url = f'https://randomuser.me/api/?gender={gender}&noinfo'
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        img_url = data['results'][0]['picture']['large']
        img_response = requests.get(img_url, timeout=5)
        img_response.raise_for_status()
        filename = f'avatar_{slugify(username)}_{gender}_{index}.jpg'
        return ContentFile(img_response.content, name=filename)
    except Exception as e:
        print(f"⚠️ Ошибка загрузки аватара для {username}: {e}")
        return None


def create_product_image(product_title, index, category_title=None):
    """Создаёт изображение товара с названием на фоне категории"""
    category_colors = {
        "Одежда": (70, 130, 180),
        "Обувь": (139, 69, 19),
        "Электроника": (25, 25, 112),
        "Дом и сад": (34, 139, 34),
        "Красота и здоровье": (255, 105, 180),
        "Спорт и отдых": (255, 140, 0),
        "Игрушки": (255, 20, 147),
        "Книги": (210, 105, 30),
    }
    if category_title and category_title in category_colors:
        bg_color = category_colors[category_title]
    else:
        bg_color = (random.randint(50, 200), random.randint(50, 200), random.randint(50, 200))
    img = Image.new("RGB", (400, 400), color=bg_color)
    draw = ImageDraw.Draw(img)
    draw.rectangle([10, 10, 390, 390], outline=(255, 255, 255), width=4)
    for i in range(0, 400, 50):
        draw.line([(i, 0), (i, 400)], fill=(255, 255, 255, 50), width=1)
        draw.line([(0, i), (400, i)], fill=(255, 255, 255, 50), width=1)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
    except:
        font = ImageFont.load_default()
    words = product_title.split()
    max_chars = 20
    lines = []
    current_line = ""
    for word in words:
        if len(current_line + " " + word) <= max_chars:
            if current_line:
                current_line += " " + word
            else:
                current_line = word
        else:
            lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
    if len(lines) > 4:
        lines = lines[:4]
        lines[-1] = lines[-1][:17] + "..."
    y_offset = 140
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (400 - text_width) // 2
        draw.rectangle([x-5, y_offset-2, x+text_width+5, y_offset+text_height+2], fill=(0, 0, 0, 128))
        draw.text((x, y_offset), line, fill=(255, 255, 255), font=font)
        y_offset += text_height + 10
    img_io = BytesIO()
    img.save(img_io, format="PNG", quality=90)
    filename = f"{slugify(product_title[:30])}_{index}_{random.randint(1000, 9999)}.png"
    return ContentFile(img_io.getvalue(), name=filename)


def generate_unique_slug(base_slug, model_class):
    slug = base_slug
    counter = 1
    while model_class.objects.filter(slug=slug).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1
    return slug


def generate_product_title(category_title, is_premium=False):
    if is_premium:
        premium_products = [
            'Apple MacBook Pro 16" M3 Max 128GB',
            "Rolex Oyster Perpetual Daytona",
            "Patek Philippe Nautilus часы",
            "Mercedes-Benz AMG GT 63 SE",
            "LV Neverfull сумка из крокодиловой кожи",
            "Dior лимитированная коллекция одежды",
            "Bentley Home дизайнерский диван",
            "B&O Beolab 90 колонки",
            "Red Octopus бриллиантовая коллекция",
            "Hermès Birkin сумка 35 см",
        ]
        return random.choice(premium_products)
    if category_title == "Одежда":
        prefixes = ["Классические", "Стильные", "Повседневные", "Элегантные", "Современные"]
        products = ["джинсы", "брюки", "футболка", "рубашка", "свитер", "платье", "юбка", "пиджак"]
        colors = ["синие", "черные", "белые", "серые", "бежевые", "зеленые", "красные"]
        return f"{random.choice(prefixes)} {random.choice(products)} {random.choice(colors)}"
    elif category_title == "Обувь":
        prefixes = ["Удобные", "Модные", "Кожаные", "Легкие", "Спортивные"]
        products = ["кроссовки", "ботинки", "туфли", "кеды", "сандалии", "сапоги"]
        colors = ["черные", "коричневые", "белые", "синие"]
        return f"{random.choice(prefixes)} {random.choice(products)} {random.choice(colors)}"
    elif category_title == "Электроника":
        brands = ["Samsung", "Apple", "Xiaomi", "Sony", "LG", "Huawei"]
        products = ["Смартфон", "Ноутбук", "Планшет", "Телевизор", "Наушники", "Колонка"]
        models = ["Pro", "Lite", "Max", "Ultra", "Air", "Plus"]
        return f"{random.choice(brands)} {random.choice(products)} {random.choice(models)}"
    elif category_title == "Дом и сад":
        prefixes = ["Уютный", "Современный", "Классический", "Практичный", "Стильный"]
        products = ["диван", "кресло", "стол", "ковер", "светильник", "ваза", "зеркало", "шкаф"]
        colors = ["бежевый", "серый", "коричневый", "белый", "черный"]
        return f"{random.choice(prefixes)} {random.choice(products)} {random.choice(colors)}"
    elif category_title == "Красота и здоровье":
        brands = ["L'Oreal", "Nivea", "Garnier", "Vichy", "La Roche"]
        products = ["крем для лица", "шампунь", "маска для волос", "парфюм", "лосьон", "скраб"]
        return f"{random.choice(brands)} {random.choice(products)}"
    elif category_title == "Спорт и отдых":
        prefixes = ["Профессиональные", "Любительские", "Удобные", "Надежные"]
        products = ["гантели", "коврик для йоги", "эспандер", "скакалка", "фитнес-браслет"]
        return f"{random.choice(prefixes)} {random.choice(products)}"
    elif category_title == "Игрушки":
        prefixes = ["Мягкая", "Развивающая", "Интерактивная", "Музыкальная"]
        products = ["игрушка", "кукла", "машинка", "конструктор", "пазл", "настольная игра"]
        return f"{random.choice(prefixes)} {random.choice(products)}"
    elif category_title == "Книги":
        genres = ["Детектив", "Роман", "Фантастика", "Биография", "Сборник рассказов"]
        return f"{random.choice(genres)} книга"
    else:
        adjectives = ["Отличный", "Качественный", "Надежный", "Современный"]
        nouns = ["товар", "аксессуар", "предмет", "изделие"]
        return f"{random.choice(adjectives)} {random.choice(nouns)}"


class Command(BaseCommand):
    help = "Генерирует тестовые данные с симпатичными аватарками и изображениями"

    def add_arguments(self, parser):
        parser.add_argument("--products", type=int, default=50, help="Количество товаров")
        parser.add_argument("--users", type=int, default=15, help="Количество покупателей")
        parser.add_argument("--reviews-per-product", type=int, default=3, help="Отзывов на товар")
        parser.add_argument("--clear", action="store_true", help="Очистить данные перед генерацией")
        parser.add_argument("--premium", action="store_true", help="Добавить дорогие премиум товары до $10,000")

    def handle(self, *args, **options):
        products_count = options["products"]
        users_count = options["users"]
        reviews_per_product = options["reviews_per_product"]
        clear = options["clear"]
        add_premium = options["premium"]

        if clear:
            self.stdout.write("🗑️ Очищаю данные и удаляю изображения...")
            old_paths = [
                os.path.join(settings.MEDIA_ROOT, "categories"),
                os.path.join(settings.MEDIA_ROOT, "product_images"),
                os.path.join(settings.MEDIA_ROOT, "catalog", "categories"),
                os.path.join(settings.MEDIA_ROOT, "catalog", "product_images"),
            ]
            for path in old_paths:
                if os.path.exists(path):
                    for file in os.listdir(path):
                        file_path = os.path.join(path, file)
                        try:
                            if os.path.isfile(file_path):
                                os.unlink(file_path)
                        except Exception:
                            pass
            Banner.objects.all().delete()
            Review.objects.all().delete()
            Sale.objects.all().delete()
            Product.objects.all().delete()
            ProductImage.objects.all().delete()
            OrderItem.objects.all().delete()
            Order.objects.all().delete()
            Category.objects.all().delete()
            Tag.objects.all().delete()
            Specification.objects.all().delete()
            Profile.objects.all().delete()
            User.objects.exclude(is_superuser=True).delete()
            self.stdout.write("   ✅ Данные и изображения очищены")
            fake.unique.clear()

        self.stdout.write("🚀 Генерация тестовых данных...")
        os.makedirs(os.path.join(settings.MEDIA_ROOT, "catalog", "categories"), exist_ok=True)
        os.makedirs(os.path.join(settings.MEDIA_ROOT, "catalog", "product_images"), exist_ok=True)

        # --- 1. Категории ---
        self.stdout.write("📁 Создаю категории...")
        categories_data = {
            "Одежда": ["Женская одежда", "Мужская одежда", "Детская одежда", "Спортивная одежда"],
            "Обувь": ["Кроссовки", "Ботинки", "Туфли", "Сандалии"],
            "Электроника": ["Смартфоны", "Ноутбуки", "Планшеты", "Наушники", "Телевизоры"],
            "Дом и сад": ["Мебель", "Посуда", "Декор", "Садовый инвентарь", "Текстиль"],
            "Красота и здоровье": ["Парфюмерия", "Косметика", "Уход за лицом", "Уход за волосами"],
            "Спорт и отдых": ["Тренажеры", "Велосипеды", "Туризм", "Фитнес аксессуары"],
            "Игрушки": ["Мягкие игрушки", "Конструкторы", "Настольные игры", "Развивающие игрушки"],
            "Книги": ["Художественная литература", "Бизнес литература", "Детские книги", "Учебники"],
        }
        for root_name, sub_names in categories_data.items():
            root_slug = generate_unique_slug(slugify(root_name), Category)
            root_image = create_category_image(root_name)
            root = Category.objects.create(title=root_name, slug=root_slug, ordering_index=random.randint(0, 100))
            root.image.save(root_image.name, root_image, save=True)
            for sub_name in sub_names:
                sub_slug = generate_unique_slug(slugify(f"{root_name}_{sub_name}"), Category)
                Category.objects.create(title=sub_name, parent=root, slug=sub_slug, ordering_index=random.randint(0, 100))
        self.stdout.write(f"   ✅ Создано {Category.objects.count()} категорий")
        all_categories = list(Category.objects.all())

        # --- 2. Теги ---
        self.stdout.write("🏷️ Создаю теги...")
        tag_names = ["хит продаж", "новинка", "распродажа", "лимитированная коллекция", "популярный",
                     "скидка 50%", "эксклюзив", "рекомендуем", "топ-10", "лучшая цена", "подарок", "хит сезона", "бестселлер"]
        tags = []
        for name in tag_names:
            tag, _ = Tag.objects.get_or_create(name=name)
            tags.append(tag)
        self.stdout.write(f"   ✅ Создано {len(tags)} тегов")

        # --- 3. Спецификации ---
        self.stdout.write("📐 Создаю спецификации...")
        specs_data = [
            ("Размер", "XS"), ("Размер", "S"), ("Размер", "M"), ("Размер", "L"), ("Размер", "XL"),
            ("Материал", "Хлопок"), ("Материал", "Шерсть"), ("Материал", "Полиэстер"),
            ("Цвет", "Белый"), ("Цвет", "Черный"), ("Цвет", "Синий"), ("Цвет", "Красный"),
            ("Страна", "Россия"), ("Страна", "Китай"), ("Страна", "Турция"),
            ("Гарантия", "6 месяцев"), ("Гарантия", "12 месяцев"), ("Гарантия", "24 месяца")
        ]
        specs = []
        for name, value in specs_data:
            spec, _ = Specification.objects.get_or_create(name=name, value=value)
            specs.append(spec)
        self.stdout.write(f"   ✅ Создано {len(specs)} спецификаций")

        # --- 4. Аватар по умолчанию ---
        default_avatar, _ = Avatar.objects.get_or_create(
            src="app_users/avatars/default.png", defaults={"alt": "Аватар по умолчанию"}
        )

        # --- 5. Пользователи ---
        try:
            client_group = Group.objects.get(name='Клиент')
            seller_group = Group.objects.get(name='Продавцы')
        except Group.DoesNotExist:
            self.stdout.write(self.style.ERROR("Группы не найдены. Запустите миграции сначала."))
            return

        self.stdout.write("👤 Создаю покупателей с паролем 123456...")
        for i in range(1, users_count + 1):
            username = f'buyer{i}'
            gender = 'male' if i % 2 == 0 else 'female'
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': f'buyer{i}@example.com',
                    'first_name': fake.first_name(),
                    'last_name': fake.last_name(),
                    'is_staff': False,
                    'is_superuser': False,
                }
            )
            if created:
                user.set_password('123456')
                user.save()
                user.groups.add(client_group)
                # Аватар
                avatar_file = download_avatar(username, gender, i)
                if avatar_file:
                    avatar_obj = Avatar.objects.create(src=avatar_file, alt=f"Avatar of {username}")
                    user.profile.avatar = avatar_obj
                else:
                    user.profile.avatar = default_avatar
                user.profile.full_name = f"{user.first_name} {user.last_name}"
                user.profile.phone = generate_phone_number()
                user.profile.balance = round(random.uniform(0, 5000), 2)
                user.profile.save()
                self.stdout.write(f"   ✅ {username}")

        self.stdout.write("👨‍💼 Создаю продавцов...")
        for i in range(1, 4):
            username = f'seller{i}'
            gender = 'male' if i % 2 == 0 else 'female'
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': f'seller{i}@example.com',
                    'first_name': fake.first_name(),
                    'last_name': fake.last_name(),
                    'is_staff': False,
                    'is_superuser': False,
                }
            )
            if created:
                user.set_password('123456')
                user.save()
                user.groups.add(seller_group)
                avatar_file = download_avatar(username, gender, i+100)
                if avatar_file:
                    avatar_obj = Avatar.objects.create(src=avatar_file, alt=f"Avatar of {username}")
                    user.profile.avatar = avatar_obj
                else:
                    user.profile.avatar = default_avatar
                user.profile.full_name = f"{user.first_name} {user.last_name}"
                user.profile.phone = generate_phone_number()
                user.profile.save()
                self.stdout.write(f"   ✅ {username}")
        self.stdout.write(f"   ✅ Покупателей: {users_count}, продавцов: 3")

        # --- Обновление профиля администратора (Брэд Питт) ---
        self.stdout.write("👑 Обновляю профиль администратора...")
        try:

            admin_user = User.objects.get(username='admin')

            # Если профиля нет — создаём вручную (сигнал не сработал в миграции)
            if not hasattr(admin_user, 'profile'):
                Profile.objects.create(user=admin_user)
                self.stdout.write("   📝 Профиль для администратора создан")

            profile = admin_user.profile
            profile.full_name = "Брэд Питт"
            profile.phone = 9991234567  # любой номер телефона

            # Скачиваем фото Брэда Питта
            avatar_file = download_avatar(admin_user.username, 'male', 999)  # Небольшой индекс для уникальности
            if avatar_file:
                avatar_obj = Avatar.objects.create(src=avatar_file, alt=f"Avatar of {admin_user.username}")
                profile.avatar = avatar_obj
                self.stdout.write("   🖼️ Аватарка администратора загружена через randomuser.me")
            else:
                # Если не загрузилось, оставляем аватар по умолчанию
                profile.avatar = default_avatar
                self.stdout.write(
                    self.style.WARNING("   ⚠️ Не удалось загрузить аватарку, оставлен аватар по умолчанию"))
            profile.save()
            self.stdout.write(self.style.SUCCESS("   ✅ Профиль администратора обновлён (Брэд Питт)"))
        except User.DoesNotExist:
            self.stdout.write(
                self.style.WARNING("   ⚠️ Администратор не найден. Убедитесь, что миграция с админом применена."))



        # --- 6. Товары ---
        self.stdout.write(f"📦 Создаю {products_count} товаров...")
        premium_products_list = []
        if add_premium:
            self.stdout.write("   💎 Добавляю премиум товары...")
            for i in range(8):
                category = random.choice(all_categories)
                cat_title = category.parent.title if category.parent else category.title
                title = generate_product_title(cat_title, is_premium=True)
                price = Decimal(str(round(random.uniform(2000, 10000), 2)))
                unique_slug = generate_unique_slug(slugify(title[:50]), Product)
                product = baker.make(
                    Product,
                    title=title,
                    category=category,
                    price=price,
                    count=random.choice([0, 1, 2, 5]),
                    description=fake.paragraph(nb_sentences=2)[:255],
                    full_description=f"🌟 ПРЕМИУМ 🌟\n\n{title}\n\n" + fake.paragraph(nb_sentences=5)[:450],
                    free_delivery=True,
                    rating=0,
                    reviews_count=0,
                    is_active=True,
                    is_limited=True,
                    ordering_index=50000 + i,
                    purchase_count=random.randint(0, 50),
                    slug=unique_slug,
                )
                for img_idx in range(random.randint(2, 4)):
                    img_file = create_product_image(title, img_idx, cat_title)
                    product_image = ProductImage(alt=f"{title} - {img_idx}")
                    product_image.image.save(img_file.name, img_file, save=True)
                    product_image.save()
                    product.images.add(product_image)
                product.tags.set(random.sample(tags, k=random.randint(2, 4)))
                premium_products_list.append(product)
            all_products_count = products_count - 8
        else:
            all_products_count = products_count

        products = []
        for i in range(all_products_count):
            category = random.choice(all_categories)
            cat_title = category.parent.title if category.parent else category.title
            title = generate_product_title(cat_title, is_premium=False)
            unique_slug = generate_unique_slug(slugify(title[:50]), Product)
            # цена
            if "Электроника" in cat_title:
                price = Decimal(str(round(random.uniform(100, 3000), 2)))
            elif "Дом" in cat_title or "Мебель" in cat_title:
                price = Decimal(str(round(random.uniform(50, 2000), 2)))
            elif "Красота" in cat_title:
                price = Decimal(str(round(random.uniform(10, 500), 2)))
            elif "Спорт" in cat_title:
                price = Decimal(str(round(random.uniform(20, 800), 2)))
            elif "Одежда" in cat_title or "Обувь" in cat_title:
                price = Decimal(str(round(random.uniform(15, 500), 2)))
            elif "Игрушки" in cat_title:
                price = Decimal(str(round(random.uniform(10, 200), 2)))
            elif "Книги" in cat_title:
                price = Decimal(str(round(random.uniform(8, 150), 2)))
            else:
                price = Decimal(str(round(random.uniform(15, 1000), 2)))
            count = 0 if random.random() < 0.2 else random.randint(1, 200)
            purchase_count = random.randint(0, 1000)
            bonus = random.randint(500, 1000) if random.random() < 0.3 else 0
            product = baker.make(
                Product,
                title=title,
                category=category,
                price=price,
                count=count,
                description=fake.paragraph(nb_sentences=2)[:255],
                full_description="\n\n".join([fake.paragraph(nb_sentences=3)])[:500],
                free_delivery=random.choice([True, False]),
                rating=0,
                reviews_count=0,
                is_active=True,
                is_limited=i < 16,
                ordering_index=purchase_count + bonus,
                purchase_count=purchase_count,
                slug=unique_slug,
            )
            for img_idx in range(random.randint(1, 3)):
                img_file = create_product_image(title, img_idx, cat_title)
                product_image = ProductImage(alt=f"{title} - {img_idx}")
                product_image.image.save(img_file.name, img_file, save=True)
                product_image.save()
                product.images.add(product_image)
            product.tags.set(random.sample(tags, k=random.randint(1, 3)))
            product.specifications.set(random.sample(specs, k=random.randint(2, 4)))
            products.append(product)
            if (i+1) % 10 == 0:
                self.stdout.write(f"   📦 {i+1}/{all_products_count} товаров")
        if add_premium:
            products.extend(premium_products_list)
        self.stdout.write(f"   ✅ Создано {len(products)} товаров")

        # --- 7. Баннеры ---
        self.stdout.write("🎯 Создаю баннеры...")
        banner_products = []
        if add_premium and premium_products_list:
            banner_products.extend(premium_products_list[:5])
        if len(banner_products) < 5:
            popular = sorted(products, key=lambda x: x.purchase_count, reverse=True)
            for prod in popular:
                if prod not in banner_products:
                    banner_products.append(prod)
                if len(banner_products) == 5:
                    break
        for prod in banner_products[:5]:
            Banner.objects.get_or_create(product=prod)
        self.stdout.write(f"   ✅ Создано {Banner.objects.count()} баннеров")



        # --- 8. Распродажи ---
        self.stdout.write("🏷️ Добавляю распродажи...")
        today = datetime.now().date()
        sales_created = 0
        for product in products:
            if random.random() < 0.4:
                discount_percent = random.randint(10, 70)
                # Вычисляем цену со скидкой, используя только Decimal
                discount_factor = Decimal(100 - discount_percent) / Decimal(100)
                sale_price = (product.price * discount_factor).quantize(Decimal('0.00'))

                start_offset = random.randint(-30, 30)
                date_from = today + timedelta(days=start_offset)
                date_to = date_from + timedelta(days=random.randint(7, 60))
                Sale.objects.get_or_create(
                    product=product,
                    defaults={
                        "sale_price": sale_price,
                        "date_from": date_from,
                        "date_to": date_to,
                    }
                )
                sales_created += 1





        # --- 9. Отзывы ---
        self.stdout.write("💬 Создаю отзывы...")
        profiles = list(Profile.objects.filter(user__groups__name='Клиент'))
        reviews_created = 0
        for product in products:
            num_reviews = random.randint(1, reviews_per_product*2)
            if profiles:
                authors = random.sample(profiles, min(num_reviews, len(profiles)))
                for author in authors:
                    baker.make(
                        Review,
                        product=product,
                        author=author,
                        text=fake.paragraph(nb_sentences=random.randint(1,5)),
                        rate=random.randint(1,5),
                        date=timezone.make_aware(fake.date_time_between(start_date="-1y", end_date="now")),
                    )
                    reviews_created += 1
            # обновить рейтинг (импорт models для Avg)
            if product.reviews.exists():
                from django.db.models import Avg
                avg = product.reviews.aggregate(Avg('rate'))['rate__avg']
                product.rating = round(avg, 2)
                product.reviews_count = product.reviews.count()
                product.save(update_fields=['rating', 'reviews_count'])
        self.stdout.write(f"   ✅ Создано {reviews_created} отзывов")

        # --- 10. Заказы ---
        self.stdout.write("📦 Создаю заказы...")
        buyers = User.objects.filter(groups__name='Клиент')
        all_products = list(Product.objects.all())
        orders_created = 0
        for buyer in buyers:
            for _ in range(random.randint(0, 3)):
                order = Order.objects.create(
                    profile=buyer.profile,
                    delivery_type=random.choice(['free', 'express', 'ordinary']),
                    payment_type=random.choice(['online', 'someone']),
                    city=fake.city(),
                    address_delivery=fake.street_address(),
                    status=random.choice(['created', 'accepted', 'paid', 'delivered', 'cancelled']),
                    created_at=fake.date_time_between(start_date='-3m', end_date='now'),
                )
                for __ in range(random.randint(1, 4)):
                    product = random.choice(all_products)
                    qty = random.randint(1, 3)
                    price_at_time = product.price
                    sale = Sale.objects.filter(
                        product=product,
                        date_from__lte=order.created_at.date(),
                        date_to__gte=order.created_at.date()
                    ).first()
                    if sale:
                        price_at_time = sale.sale_price
                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        quantity=qty,
                        price_at_time=price_at_time
                    )
                order.calculate_total_cost()
                orders_created += 1
        self.stdout.write(f"   ✅ Создано {orders_created} заказов")

        # --- ИТОГ ---
        self.stdout.write(self.style.SUCCESS(
            f"\n✨ ГОТОВО!\n"
            f"📁 Категорий: {Category.objects.count()}\n"
            f"🏷️ Тегов: {Tag.objects.count()}\n"
            f"📐 Спецификаций: {Specification.objects.count()}\n"
            f"📦 Товаров: {Product.objects.count()}\n"
            f"🖼️ Изображений товаров: {ProductImage.objects.count()}\n"
            f"🎯 Баннеров: {Banner.objects.count()}\n"
            f"🏷️ Распродаж: {Sale.objects.count()}\n"
            f"💬 Отзывов: {Review.objects.count()}\n"
            f"👤 Пользователей: {User.objects.count()}\n"
            f"📦 Заказов: {Order.objects.count()}\n"
            f"📦 Позиций в заказах: {OrderItem.objects.count()}\n"
        ))