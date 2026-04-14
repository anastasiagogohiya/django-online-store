from django.contrib import admin
from .models import Category, Product, ProductImage



@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon', 'parent_category', 'is_active', 'ordering_index')
    list_filter = ('is_active', 'parent_category') # фильтрация по Активен и по Главной категории товаров
    search_fields = ('name', 'parent_category')
    prepopulated_fields = {'slug': ('name',)} # автоматическое заполнение slug


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'is_active')
    list_filter = ('is_active', 'is_limited', 'category')
    search_fields = ('name', 'category')
    prepopulated_fields = {'slug': ('name',)} # автоматическое заполнение slug


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ('product', 'image', 'is_main')
    list_filter = ('is_main',)