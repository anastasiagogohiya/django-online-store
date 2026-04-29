import random
import os
from io import BytesIO
from django.core.management.base import BaseCommand
from django.db import models
from model_bakery import baker
from faker import Faker
from django.utils.text import slugify
from datetime import datetime, timedelta
from django.core.files.base import ContentFile
from PIL import Image, ImageDraw, ImageFont
from catalog.models import Category, Tag, Specification, Product, Review, ProductImage, Sale, \
    Banner  # Добавлен импорт Banner
from app_users.models import Profile, Avatar
from django.contrib.auth.models import User
from django.conf import settings

fake = Faker('ru_RU')


def generate_phone_number():
    """Генерирует телефон в формате только цифр (10 цифр)"""
    return int(f"9{random.randint(100000000, 999999999)}")


def create_category_image(category_name):
    """Создает реальный файл изображения для категории"""
    colors = {
        'Одежда': (100, 150, 200),
        'Обувь': (150, 100, 100),
        'Электроника': (100, 200, 100),
        'Дом и сад': (200, 150, 100),
        'Красота и здоровье': (200, 100, 150),
        'Спорт и отдых': (100, 200, 150),
        'Игрушки': (200, 200, 100),
        'Книги': (150, 100, 200),
    }

    color = colors.get(category_name, (random.randint(100, 200), random.randint(100, 200), random.randint(100, 200)))

    img = Image.new('RGB', (600, 400), color=color)
    draw = ImageDraw.Draw(img)

    draw.rectangle([10, 10, 590, 390], outline=(255, 255, 255), width=3)

    try:
        font = ImageFont.load_default()
        text = category_name[:25]
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (600 - text_width) // 2
        y = (400 - text_height) // 2
        draw.text((x, y), text, fill=(255, 255, 255), font=font)
    except:
        draw.text((50, 180), category_name[:20], fill=(255, 255, 255))

    img_io = BytesIO()
    img.save(img_io, format='PNG', quality=90)
    filename = f"{slugify(category_name)[:30]}_{random.randint(1000, 9999)}.png"
    return ContentFile(img_io.getvalue(), name=filename)


def create_product_image(product_title, index):
    """Создает реальный файл изображения для товара"""
    color = (random.randint(100, 200), random.randint(100, 200), random.randint(100, 200))

    img = Image.new('RGB', (400, 400), color=color)

    draw = ImageDraw.Draw(img)
    for i in range(0, 400, 50):
        draw.line([(i, 0), (i, 400)], fill=(255, 255, 255), width=2)
        draw.line([(0, i), (400, i)], fill=(255, 255, 255), width=2)

    draw.rectangle([10, 10, 390, 390], outline=(255, 255, 255), width=3)

    img_io = BytesIO()
    img.save(img_io, format='PNG', quality=90)
    filename = f"{slugify(product_title[:30])}_{index}_{random.randint(1000, 9999)}.png"
    return ContentFile(img_io.getvalue(), name=filename)


def generate_unique_slug(base_slug, model_class):
    """Генерирует уникальный slug"""
    slug = base_slug
    counter = 1
    while model_class.objects.filter(slug=slug).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1
    return slug


def generate_product_title(category_title, is_premium=False):
    """Генерирует логичное название товара на русском языке"""

    # Дорогие премиум товары
    if is_premium:
        premium_products = [
            'Apple MacBook Pro 16" M3 Max 128GB',
            'Rolex Oyster Perpetual Daytona',
            'Patek Philippe Nautilus часы',
            'Mercedes-Benz AMG GT 63 SE',
            'LV Neverfull сумка из крокодиловой кожи',
            'Dior лимитированная коллекция одежды',
            'Bentley Home дизайнерский диван',
            'B&O Beolab 90 колонки',
            'Red Octopus бриллиантовая коллекция',
            'Hermès Birkin сумка 35 см'
        ]
        return random.choice(premium_products)

    if category_title == 'Одежда':
        prefixes = ['Классические', 'Стильные', 'Повседневные', 'Элегантные', 'Современные']
        products = ['джинсы', 'брюки', 'футболка', 'рубашка', 'свитер', 'платье', 'юбка', 'пиджак']
        colors = ['синие', 'черные', 'белые', 'серые', 'бежевые', 'зеленые', 'красные']
        return f"{random.choice(prefixes)} {random.choice(products)} {random.choice(colors)}"

    elif category_title == 'Обувь':
        prefixes = ['Удобные', 'Модные', 'Кожаные', 'Легкие', 'Спортивные']
        products = ['кроссовки', 'ботинки', 'туфли', 'кеды', 'сандалии', 'сапоги']
        colors = ['черные', 'коричневые', 'белые', 'синие']
        return f"{random.choice(prefixes)} {random.choice(products)} {random.choice(colors)}"

    elif category_title == 'Электроника':
        brands = ['Samsung', 'Apple', 'Xiaomi', 'Sony', 'LG', 'Huawei']
        products = ['Смартфон', 'Ноутбук', 'Планшет', 'Телевизор', 'Наушники', 'Колонка']
        models = ['Pro', 'Lite', 'Max', 'Ultra', 'Air', 'Plus']
        return f"{random.choice(brands)} {random.choice(products)} {random.choice(models)}"

    elif category_title == 'Дом и сад':
        prefixes = ['Уютный', 'Современный', 'Классический', 'Практичный', 'Стильный']
        products = ['диван', 'кресло', 'стол', 'ковер', 'светильник', 'ваза', 'зеркало', 'шкаф']
        colors = ['бежевый', 'серый', 'коричневый', 'белый', 'черный']
        return f"{random.choice(prefixes)} {random.choice(products)} {random.choice(colors)}"

    elif category_title == 'Красота и здоровье':
        brands = ['L\'Oreal', 'Nivea', 'Garnier', 'Vichy', 'La Roche']
        products = ['крем для лица', 'шампунь', 'маска для волос', 'парфюм', 'лосьон', 'скраб']
        return f"{random.choice(brands)} {random.choice(products)}"

    elif category_title == 'Спорт и отдых':
        prefixes = ['Профессиональные', 'Любительские', 'Удобные', 'Надежные']
        products = ['гантели', 'коврик для йоги', 'эспандер', 'скакалка', 'фитнес-браслет']
        return f"{random.choice(prefixes)} {random.choice(products)}"

    elif category_title == 'Игрушки':
        prefixes = ['Мягкая', 'Развивающая', 'Интерактивная', 'Музыкальная']
        products = ['игрушка', 'кукла', 'машинка', 'конструктор', 'пазл', 'настольная игра']
        return f"{random.choice(prefixes)} {random.choice(products)}"

    elif category_title == 'Книги':
        genres = ['Детектив', 'Роман', 'Фантастика', 'Биография', 'Сборник рассказов']
        return f"{random.choice(genres)} книга"

    elif category_title in ['Женская одежда', 'Мужская одежда', 'Детская одежда']:
        sizes = ['S', 'M', 'L', 'XL']
        colors = ['белый', 'черный', 'синий', 'красный', 'серый']
        if 'женская' in category_title.lower():
            return f"Женская футболка {random.choice(colors)} размера {random.choice(sizes)}"
        elif 'мужская' in category_title.lower():
            return f"Мужская рубашка {random.choice(colors)} размера {random.choice(sizes)}"
        else:
            return f"Детские штаны {random.choice(colors)} размера {random.choice(sizes)}"

    elif category_title in ['Смартфоны', 'Ноутбуки', 'Планшеты']:
        brands = ['Samsung', 'Apple', 'Xiaomi']
        models = ['A-серия', 'Galaxy', 'iPhone', 'Redmi']
        return f"{random.choice(brands)} {category_title[:-1]} {random.choice(models)}"

    elif category_title in ['Мебель', 'Посуда', 'Декор']:
        if category_title == 'Посуда':
            return f"Набор посуды {random.choice(['эмалированный', 'керамический', 'стеклянный'])} {random.randint(6, 24)} предметов"
        elif category_title == 'Декор':
            return f"Декоративная {random.choice(['ваза', 'картина', 'свеча', 'статуэтка'])} {random.choice(['золотая', 'серебряная', 'деревянная'])}"
        else:
            return f"Угловой диван {random.choice(['велюровый', 'кожаный', 'тканевый'])} {random.choice(['бежевый', 'серый', 'коричневый'])}"

    else:
        adjectives = ['Отличный', 'Качественный', 'Надежный', 'Современный']
        nouns = ['товар', 'аксессуар', 'предмет', 'изделие']
        return f"{random.choice(adjectives)} {random.choice(nouns)}"


class Command(BaseCommand):
    help = 'Генерирует реалистичные тестовые данные с реальными изображениями'

    def add_arguments(self, parser):
        parser.add_argument('--products', type=int, default=50, help='Количество товаров')
        parser.add_argument('--users', type=int, default=15, help='Количество пользователей')
        parser.add_argument('--reviews-per-product', type=int, default=3, help='Отзывов на товар')
        parser.add_argument('--clear', action='store_true', help='Очистить данные перед генерацией')
        parser.add_argument('--premium', action='store_true', help='Добавить дорогие премиум товары до $10,000')

    def handle(self, *args, **options):
        products_count = options['products']
        users_count = options['users']
        reviews_per_product = options['reviews_per_product']
        clear = options['clear']
        add_premium = options['premium']

        if clear:
            self.stdout.write('🗑️ Очищаю данные и удаляю изображения...')

            # Удаляем старые папки
            old_paths = [
                os.path.join(settings.MEDIA_ROOT, 'categories'),
                os.path.join(settings.MEDIA_ROOT, 'product_images'),
                os.path.join(settings.MEDIA_ROOT, 'catalog', 'categories'),
                os.path.join(settings.MEDIA_ROOT, 'catalog', 'product_images'),
            ]

            for path in old_paths:
                if os.path.exists(path):
                    for file in os.listdir(path):
                        file_path = os.path.join(path, file)
                        try:
                            if os.path.isfile(file_path):
                                os.unlink(file_path)
                        except Exception as e:
                            pass

            # Очищаем БД
            Banner.objects.all().delete()  # Очищаем баннеры
            Review.objects.all().delete()
            Sale.objects.all().delete()  # Очищаем распродажи
            Product.objects.all().delete()
            ProductImage.objects.all().delete()
            Category.objects.all().delete()
            Tag.objects.all().delete()
            Specification.objects.all().delete()
            Profile.objects.all().delete()
            User.objects.exclude(is_superuser=True).delete()

            self.stdout.write('   ✅ Данные и изображения очищены')
            fake.unique.clear()

        self.stdout.write('🚀 Генерация тестовых данных...')
        self.stdout.write(f'📁 MEDIA_ROOT = {settings.MEDIA_ROOT}')

        # Создаем нужные директории
        os.makedirs(os.path.join(settings.MEDIA_ROOT, 'catalog', 'categories'), exist_ok=True)
        os.makedirs(os.path.join(settings.MEDIA_ROOT, 'catalog', 'product_images'), exist_ok=True)

        self.stdout.write(f'   ✅ Директории созданы:')
        self.stdout.write(f'      - {os.path.join(settings.MEDIA_ROOT, "catalog", "categories")}')
        self.stdout.write(f'      - {os.path.join(settings.MEDIA_ROOT, "catalog", "product_images")}')

        # --- 1. Категории ---
        self.stdout.write('📁 Создаю категории с изображениями...')

        categories_data = {
            'Одежда': ['Женская одежда', 'Мужская одежда', 'Детская одежда', 'Спортивная одежда'],
            'Обувь': ['Кроссовки', 'Ботинки', 'Туфли', 'Сандалии'],
            'Электроника': ['Смартфоны', 'Ноутбуки', 'Планшеты', 'Наушники', 'Телевизоры'],
            'Дом и сад': ['Мебель', 'Посуда', 'Декор', 'Садовый инвентарь', 'Текстиль'],
            'Красота и здоровье': ['Парфюмерия', 'Косметика', 'Уход за лицом', 'Уход за волосами'],
            'Спорт и отдых': ['Тренажеры', 'Велосипеды', 'Туризм', 'Фитнес аксессуары'],
            'Игрушки': ['Мягкие игрушки', 'Конструкторы', 'Настольные игры', 'Развивающие игрушки'],
            'Книги': ['Художественная литература', 'Бизнес литература', 'Детские книги', 'Учебники'],
        }

        for root_name, sub_names in categories_data.items():
            root_slug = generate_unique_slug(slugify(root_name), Category)
            root_image = create_category_image(root_name)

            root = Category.objects.create(
                title=root_name,
                slug=root_slug,
                ordering_index=random.randint(0, 100)
            )
            root.image.save(root_image.name, root_image, save=True)
            self.stdout.write(f'   📸 Изображение категории "{root_name}" сохранено: {root.image.path}')

            for sub_name in sub_names:
                sub_slug = generate_unique_slug(slugify(f"{root_name}_{sub_name}"), Category)
                Category.objects.create(
                    title=sub_name,
                    parent=root,
                    slug=sub_slug,
                    ordering_index=random.randint(0, 100)
                )

        self.stdout.write(f'   ✅ Создано {Category.objects.count()} категорий')

        # --- 2. Теги ---
        self.stdout.write('🏷️ Создаю теги...')

        tag_names = [
            'хит продаж', 'новинка', 'распродажа', 'лимитированная коллекция',
            'популярный', 'скидка 50%', 'эксклюзив', 'рекомендуем', 'топ-10',
            'лучшая цена', 'подарок', 'хит сезона', 'бестселлер'
        ]

        tags = []
        for name in tag_names:
            tag, created = Tag.objects.get_or_create(name=name)
            tags.append(tag)

        self.stdout.write(f'   ✅ Создано {len(tags)} тегов')

        # --- 3. Спецификации ---
        self.stdout.write('📐 Создаю спецификации...')

        specs_data = [
            ('Размер', 'XS'), ('Размер', 'S'), ('Размер', 'M'), ('Размер', 'L'), ('Размер', 'XL'),
            ('Материал', 'Хлопок'), ('Материал', 'Шерсть'), ('Материал', 'Полиэстер'),
            ('Цвет', 'Белый'), ('Цвет', 'Черный'), ('Цвет', 'Синий'), ('Цвет', 'Красный'),
            ('Страна', 'Россия'), ('Страна', 'Китай'), ('Страна', 'Турция'),
            ('Гарантия', '6 месяцев'), ('Гарантия', '12 месяцев'), ('Гарантия', '24 месяца'),
        ]

        specs = []
        for name, value in specs_data:
            spec, created = Specification.objects.get_or_create(name=name, value=value)
            specs.append(spec)

        self.stdout.write(f'   ✅ Создано {len(specs)} спецификаций')

        # --- 4. Аватар ---
        default_avatar, created = Avatar.objects.get_or_create(
            src='app_users/avatars/default.png',
            defaults={'alt': 'Аватар по умолчанию'}
        )

        # --- 5. Пользователи ---
        self.stdout.write(f'👤 Создаю {users_count} пользователей...')

        users = baker.make(
            User,
            _quantity=users_count,
            first_name=lambda: fake.first_name(),
            last_name=lambda: fake.last_name(),
            email=lambda: fake.unique.email(),
            username=lambda: fake.unique.user_name(),
            is_active=True,
        )

        self.stdout.write(f'   👤 Обновляю профили пользователей...')
        for user in users:
            # Профиль уже создан сигналом, просто обновляем поля
            profile = user.profile
            profile.full_name = f"{user.first_name} {user.last_name}"
            profile.email = user.email
            profile.phone = generate_phone_number()
            profile.avatar = default_avatar
            profile.balance = round(random.uniform(0, 5000), 2)
            profile.save()

        self.stdout.write(f'   ✅ Обновлено {users_count} профилей')

        # --- 6. Товары ---
        self.stdout.write(f'📦 Создаю {products_count} товаров с изображениями...')

        # Создаем дорогие премиум товары
        premium_products_list = []
        if add_premium:
            self.stdout.write('   💎 Добавляю дорогие премиум товары...')
            for i in range(8):  # 8 дорогих товаров
                category = random.choice(all_categories)
                title = generate_product_title(category.title if category.parent else category.title, is_premium=True)

                # Цена от $2,000 до $10,000
                price = round(random.uniform(2000, 10000), 2)

                unique_slug = generate_unique_slug(slugify(title[:50]), Product)

                product = baker.make(
                    Product,
                    title=title,
                    category=category,
                    price=price,
                    count=random.choice([0, 1, 2, 5]),  # Некоторые с нулевым наличием
                    description=fake.paragraph(nb_sentences=2)[:255],
                    full_description=f"🌟 ЭКСКЛЮЗИВНЫЙ ПРЕМИУМ ТОВАР 🌟\n\n{title} - это воплощение роскоши и качества.\n\n" + fake.paragraph(
                        nb_sentences=5)[:450],
                    free_delivery=True,
                    rating=0,
                    reviews_count=0,
                    is_active=True,
                    is_limited=True,
                    ordering_index=50000 + i,  # Высокий индекс
                    purchase_count=random.randint(0, 50),
                    slug=unique_slug,
                )

                # Добавляем изображения
                for img_index in range(random.randint(2, 4)):
                    img_file = create_product_image(title, img_index)
                    product_image = ProductImage.objects.create(alt=f"{title} - изображение {img_index + 1}")
                    product_image.image.save(img_file.name, img_file, save=True)
                    product.images.add(product_image)

                product.tags.set(random.sample(tags, k=random.randint(2, 4)))
                premium_products_list.append(product)

                self.stdout.write(f'      💎 {title} — ${price}')

            all_products_count = products_count - 8
        else:
            all_products_count = products_count

        all_categories = list(Category.objects.all())

        products = []
        product_images_list = []

        for i in range(all_products_count):
            category = random.choice(all_categories)
            parent_category = category.parent.title if category.parent else category.title
            title = generate_product_title(parent_category, is_premium=False)

            base_slug = slugify(title[:50])
            unique_slug = generate_unique_slug(base_slug, Product)

            # Генерация цены с возможностью дорогих товаров
            if 'Электроника' in parent_category or 'Смартфоны' in parent_category or 'Ноутбуки' in parent_category:
                price = round(random.uniform(100, 3000), 2)  # До $3,000
            elif 'Дом' in parent_category or 'Мебель' in parent_category:
                price = round(random.uniform(50, 2000), 2)  # До $2,000
            elif 'Красота' in parent_category:
                price = round(random.uniform(10, 500), 2)
            elif 'Спорт' in parent_category:
                price = round(random.uniform(20, 800), 2)
            elif 'Одежда' in parent_category or 'Обувь' in parent_category:
                price = round(random.uniform(15, 500), 2)
            elif 'Игрушки' in parent_category:
                price = round(random.uniform(10, 200), 2)
            elif 'Книги' in parent_category:
                price = round(random.uniform(8, 150), 2)
            else:
                price = round(random.uniform(15, 1000), 2)

            # Некоторые товары получают нулевое наличие (20% товаров)
            if random.random() < 0.2:
                count = 0
                availability_status = "❌ НЕТ В НАЛИЧИИ"
            else:
                count = random.randint(1, 200)
                availability_status = "✅ В НАЛИЧИИ"

            # Индекс = популярность + ручной приоритет
            purchase_count = random.randint(0, 1000)

            # Некоторые товары получают бонус к индексу
            bonus = 0
            if random.random() < 0.3:  # 30% товаров - "продвигаемые"
                bonus = random.randint(500, 1000)

            product = baker.make(
                Product,
                title=title,
                category=category,
                price=price,
                count=count,
                description=fake.paragraph(nb_sentences=2)[:255],
                full_description='\n\n'.join([
                    fake.paragraph(nb_sentences=3),
                    f"✨ Характеристики:\n- {random.choice(specs_data)[0]}: {random.choice(specs_data)[1]}\n- Гарантия: {random.randint(6, 24)} месяцев"
                ])[:500],
                free_delivery=random.choice([True, False]),
                rating=0,
                reviews_count=0,
                is_active=True,
                is_limited=i < 16,
                ordering_index=purchase_count + bonus,
                purchase_count=purchase_count,
                slug=unique_slug,
            )

            product_images = []
            for img_index in range(random.randint(1, 3)):
                img_file = create_product_image(title, img_index)
                product_image = ProductImage.objects.create(
                    alt=f"{title} - изображение {img_index + 1}"
                )
                product_image.image.save(img_file.name, img_file, save=True)
                product_images.append(product_image)
                product_images_list.append(product_image)

            product.images.set(product_images)
            product.tags.set(random.sample(tags, k=random.randint(1, 3)))
            product.specifications.set(random.sample(specs, k=random.randint(2, 4)))

            products.append(product)

            if (i + 1) % 10 == 0:
                self.stdout.write(f'   📦 Создано {i + 1}/{all_products_count} товаров')

        # Объединяем обычные и премиум товары
        if add_premium:
            products.extend(premium_products_list)
            self.stdout.write(f'   ✅ Создано {len(products)} товаров (включая {len(premium_products_list)} премиум)')
        else:
            self.stdout.write(f'   ✅ Создано {len(products)} товаров')

        self.stdout.write(f'   🖼️ Создано {len(product_images_list)} изображений')

        # --- 7. БАННЕРЫ (добавляем 5 товаров в баннеры) ---
        self.stdout.write('🎯 Создаю баннеры для главной страницы...')

        banner_products = []

        # Добавляем премиум товары (не более 5)
        if add_premium and premium_products_list:
            banner_products.extend(premium_products_list[:5])

        # Если не хватает до 5, добавляем популярными
        if len(banner_products) < 5:
            popular_products = sorted(products, key=lambda x: x.purchase_count, reverse=True)
            for prod in popular_products:
                if prod not in banner_products:
                    banner_products.append(prod)
                if len(banner_products) == 5:
                    break

        # Обрезаем ровно до 5
        banner_products = banner_products[:5]

        banners_created = 0
        for idx, product in enumerate(banner_products):
            # Убираем defaults - поле ordering_index не нужно
            banner, created = Banner.objects.get_or_create(product=product)

            if created:
                banners_created += 1
                self.stdout.write(f'   🎯 Баннер {idx + 1}: {product.title} — ${product.price}')

        self.stdout.write(f'   ✅ Создано {banners_created} баннеров')








        # --- 8. Распродажи (Sales) ---
        self.stdout.write('🏷️ Добавляю распродажи для товаров...')

        sales_created = 0
        today = datetime.now().date()

        for product in products:
            # 40% товаров получают скидку
            if random.random() < 0.4:
                discount_percent = random.randint(10, 70)
                sale_price = round(product.price * (1 - discount_percent / 100), 2)

                start_offset = random.randint(-30, 30)
                date_from = today + timedelta(days=start_offset)
                duration = random.randint(7, 60)
                date_to = date_from + timedelta(days=duration)

                sale, created = Sale.objects.get_or_create(
                    product=product,
                    defaults={
                        'sale_price': sale_price,
                        'date_from': date_from,
                        'date_to': date_to,
                    }
                )

                if created:
                    sales_created += 1

                    if sales_created <= 5:
                        self.stdout.write(
                            f'   🏷️ Товар "{product.title[:30]}..." - '
                            f'цена: {product.price} → {sale_price} '
                            f'(скидка {discount_percent}%)'
                        )

        self.stdout.write(f'   ✅ Создано {sales_created} распродаж')

        # --- 9. Отзывы ---
        self.stdout.write('💬 Создаю отзывы...')

        # Получаем список всех профилей (так как author связан с Profile)
        all_profiles = list(Profile.objects.all())
        all_products = list(Product.objects.all())

        reviews_created = 0
        reviews_per_product = options['reviews_per_product']

        for product in all_products:
            num_reviews = random.randint(1, reviews_per_product * 2)

            # Выбираем случайных авторов (профили)
            potential_authors = random.sample(all_profiles, min(num_reviews, len(all_profiles)))

            for author in potential_authors:
                review = baker.make(
                    Review,
                    product=product,
                    author=author,  # связь с Profile
                    text=fake.paragraph(nb_sentences=random.randint(1, 5)),
                    rate=random.randint(1, 5),  # поле называется rate, не rating!
                    date=fake.date_time_between(start_date='-1y', end_date='now'),
                    # is_active - нет такого поля
                )
                reviews_created += 1

        # Обновляем рейтинг товаров после создания отзывов
        for product in all_products:
            reviews = product.reviews.all()
            if reviews.exists():
                # Вычисляем средний рейтинг
                avg_rating = sum(r.rate for r in reviews) / reviews.count()
                product.rating = round(avg_rating, 2)
                product.reviews_count = reviews.count()
                product.save()

        self.stdout.write(f'   ✅ Создано {reviews_created} отзывов')









        # --- ИТОГ ---
        self.stdout.write(self.style.SUCCESS(
            f'\n✨ ГОТОВО! ✨\n'
            f'   📁 Категории: {Category.objects.count()}\n'
            f'   🏷️ Теги: {Tag.objects.count()}\n'
            f'   📐 Спецификации: {Specification.objects.count()}\n'
            f'   🖼️ Изображения товаров: {ProductImage.objects.count()}\n'
            f'   📦 Товары: {Product.objects.count()}\n'
            f'   🎯 Баннеры: {Banner.objects.count()}\n'
            f'   🏷️ Распродажи: {Sale.objects.count()}\n'
            f'   💬 Отзывы: {Review.objects.count()}\n'
            f'   👤 Пользователи: {User.objects.count()}\n'
            f'   👥 Профили: {Profile.objects.count()}'
        ))

        # Статистика по наличию товаров
        out_of_stock = Product.objects.filter(count=0).count()
        in_stock = Product.objects.filter(count__gt=0).count()
        self.stdout.write(self.style.SUCCESS(
            f'\n📊 Статистика наличия товаров:\n'
            f'   ✅ В наличии: {in_stock} товаров\n'
            f'   ❌ Нет в наличии: {out_of_stock} товаров\n'
            f'   💰 Самый дорогой товар: ${max(p.price for p in products):.2f}'
        ))

        self.stdout.write(self.style.SUCCESS(
            f'\n📁 Изображения сохранены в:\n'
            f'   - Категории: {os.path.join(settings.MEDIA_ROOT, "catalog", "categories")}/\n'
            f'   - Товары: {os.path.join(settings.MEDIA_ROOT, "catalog", "product_images")}/'
        ))

        if products:
            self.stdout.write(self.style.SUCCESS('\n📌 Примеры созданных товаров:'))
            for i, sample in enumerate(products[:10]):  # Показываем 10 товаров
                stock_status = "❌ Нет в наличии" if sample.count == 0 else f"✅ {sample.count} шт"
                self.stdout.write(self.style.SUCCESS(
                    f'   {i + 1}. {sample.title[:50]} — ${sample.price} ({stock_status})'
                ))

            # Дополнительный вывод информации об индексах сортировки
            self.stdout.write(self.style.SUCCESS('\n📊 Информация об индексах сортировки:'))
            promoted_count = sum(1 for p in products if p.ordering_index > p.purchase_count)
            self.stdout.write(self.style.SUCCESS(
                f'   - Продвигаемых товаров (с бонусом): {promoted_count} из {len(products)}'
            ))
            self.stdout.write(self.style.SUCCESS(
                f'   - Диапазон индексов сортировки: от {min(p.ordering_index for p in products)} до {max(p.ordering_index for p in products)}'
            ))