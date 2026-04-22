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
from catalog.models import Category, Tag, Specification, Product, Review, ProductImage
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
    # ТОЛЬКО ИМЯ ФАЙЛА, БЕЗ ПАПОК! upload_to добавит папку catalog/categories/
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
    # ТОЛЬКО ИМЯ ФАЙЛА, БЕЗ ПАПОК! upload_to добавит папку catalog/product_images/
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


def generate_product_title(category_title):
    """Генерирует логичное название товара на русском языке"""

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

    def handle(self, *args, **options):
        products_count = options['products']
        users_count = options['users']
        reviews_per_product = options['reviews_per_product']
        clear = options['clear']

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
            Review.objects.all().delete()
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
            ('Гарантия', '6 месяцев'), ('Гарантия', '12 месяцев'),
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

        profiles = baker.make(
            Profile,
            _quantity=users_count,
            user=iter(users),
            full_name=lambda: f"{fake.first_name()} {fake.last_name()}",
            email=lambda: fake.email(),
            phone=generate_phone_number,
            is_active=True,
            avatar=default_avatar,
            balance=lambda: round(random.uniform(0, 5000), 2),
        )

        self.stdout.write(f'   ✅ Создано {len(profiles)} профилей')

        # --- 6. Товары ---
        self.stdout.write(f'📦 Создаю {products_count} товаров с изображениями...')

        all_categories = list(Category.objects.all())

        products = []
        product_images_list = []

        for i in range(products_count):
            category = random.choice(all_categories)
            parent_category = category.parent.title if category.parent else category.title
            title = generate_product_title(parent_category)

            base_slug = slugify(title[:50])
            unique_slug = generate_unique_slug(base_slug, Product)

            if 'Электроника' in parent_category or 'Смартфоны' in parent_category or 'Ноутбуки' in parent_category:
                price = round(random.uniform(100, 1500), 2)
            elif 'Дом' in parent_category or 'Мебель' in parent_category:
                price = round(random.uniform(30, 500), 2)
            elif 'Красота' in parent_category:
                price = round(random.uniform(10, 100), 2)
            elif 'Спорт' in parent_category:
                price = round(random.uniform(20, 300), 2)
            elif 'Одежда' in parent_category or 'Обувь' in parent_category:
                price = round(random.uniform(15, 150), 2)
            elif 'Игрушки' in parent_category:
                price = round(random.uniform(10, 80), 2)
            elif 'Книги' in parent_category:
                price = round(random.uniform(8, 50), 2)
            else:
                price = round(random.uniform(15, 200), 2)

            # Индекс = популярность + ручной приоритет
            purchase_count = random.randint(0, 1000)

            # Некоторые товары получают бонус к индексу
            bonus = 0
            if random.random() < 0.3:  # 30% товаров - "продвигаемые"
                bonus = random.randint(500, 1000)  # Большой бонус

            product = baker.make(
                Product,
                title=title,
                category=category,
                price=price,
                count=random.randint(0, 200),
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
                ordering_index=purchase_count + bonus,  # Индекс = покупки + бонус
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

                if i < 3 and img_index == 0:
                    self.stdout.write(f'   📸 Изображение товара сохранено: {product_image.image.path}')

            product.images.set(product_images)
            product.tags.set(random.sample(tags, k=random.randint(1, 3)))
            product.specifications.set(random.sample(specs, k=random.randint(2, 4)))

            products.append(product)

            if (i + 1) % 10 == 0:
                self.stdout.write(f'   📦 Создано {i + 1}/{products_count} товаров')

        self.stdout.write(f'   ✅ Создано {len(products)} товаров и {len(product_images_list)} изображений')

        # --- 7. Отзывы ---
        self.stdout.write(f'💬 Создаю отзывы...')

        reviews_created = 0
        for product in products:
            num_reviews = random.randint(0, reviews_per_product * 2)

            for _ in range(num_reviews):
                start_date = datetime.now() - timedelta(days=180)
                end_date = datetime.now()

                review = baker.make(
                    Review,
                    product=product,
                    author=random.choice(profiles),
                    text=fake.paragraph(nb_sentences=random.randint(2, 4))[:500],
                    rate=random.randint(1, 5),
                    date=fake.date_time_between(start_date=start_date, end_date=end_date),
                )
                reviews_created += 1

            if product.reviews.count() > 0:
                avg_rating = product.reviews.aggregate(models.Avg('rate'))['rate__avg']
                product.rating = round(avg_rating, 2)
                product.reviews_count = product.reviews.count()
                product.save(update_fields=['rating', 'reviews_count'])

        self.stdout.write(f'   ✅ Создано {reviews_created} отзывов')

        # --- ИТОГ ---
        self.stdout.write(self.style.SUCCESS(
            f'\n✨ ГОТОВО! ✨\n'
            f'   📁 Категории: {Category.objects.count()}\n'
            f'   🏷️ Теги: {Tag.objects.count()}\n'
            f'   📐 Спецификации: {Specification.objects.count()}\n'
            f'   🖼️ Изображения товаров: {ProductImage.objects.count()}\n'
            f'   📦 Товары: {Product.objects.count()}\n'
            f'   💬 Отзывы: {Review.objects.count()}\n'
            f'   👤 Пользователи: {User.objects.count()}\n'
            f'   👥 Профили: {Profile.objects.count()}'
        ))

        self.stdout.write(self.style.SUCCESS(
            f'\n📁 Изображения сохранены в:\n'
            f'   - Категории: {os.path.join(settings.MEDIA_ROOT, "catalog", "categories")}/\n'
            f'   - Товары: {os.path.join(settings.MEDIA_ROOT, "catalog", "product_images")}/'
        ))

        if products:
            self.stdout.write(self.style.SUCCESS('\n📌 Примеры созданных товаров:'))
            for i, sample in enumerate(products[:5]):
                self.stdout.write(self.style.SUCCESS(
                    f'   {i + 1}. {sample.title} — ${sample.price} ({sample.category.title})'
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