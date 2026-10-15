-- Все активные пользоватали с фамилией начинающейся с А, email, телефон
select au.last_name, au.first_name, au.email, aup.phone
from auth_user au
left join app_users_profile aup on au.id = aup.user_id
where au.last_name like 'А%' and au.is_active = True;

-- Топ 3 клиентов по каждому городу, купившие (статус доставлено)
-- на макс сумму заказов за год от текущ даты
-- Хотим сделать подарок на НГ: увеличить скидку на будущие заказы:
-- 1 место - 30%, 2 место - 20%, 3 место - 10%
with ranked AS( -- делаем табличное выражение
select oo.city,
oo.profile_id,
aup.full_name,
SUM(oo.total_cost::numeric) AS total_sum,
dense_rank() over (partition by oo.city
order by SUM(oo.total_cost::numeric) DESC) as rnk -- ранжируем при одинаковых значениях присваивается тот же ранг (чтобы было честно) разделяем по городам по убыванию
from order_order oo
join app_users_profile aup on aup.id = oo.profile_id
where oo.status = 'delivered' and oo.created_at >= now() - interval '1 year'
group by oo.city, oo.profile_id, aup.full_name)
select city, full_name, total_sum, rnk,
case rnk
when 1 then 30 -- топ 1 получает 30% скидки
when 2 then 20 -- топ 2 получает 20% скидки
when 3 then 10 -- топ 3 получает 10% скидки
else 0 -- best practice
end as happy_new_year_discount
from ranked where rnk <= 3  -- только топ 3
order by rnk, city;

