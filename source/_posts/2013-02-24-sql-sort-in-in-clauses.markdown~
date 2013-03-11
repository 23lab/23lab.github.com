---
layout: post
title: "SQL中结果集按IN子句中id顺序排序"
date: 2012-12-24 15:58
comments: true
categories: 
---

今天突然想到一个问题, 如果我在MySQL数据库表中数据id有, 1, 2, 3, 4, 5, 其中使用了IN子句进行查询, 查询语句为.

{% codeblock lang:sql %}
SELECT id FROM tbl WHERE id IN(1, 5, 3);
{% endcodeblock %}

此SQL出来的内容肯定是

{% codeblock %}
1
3
5
{% endcodeblock %}

那如果我想要出来的顺序和IN子句中顺序一样怎么办呢？这里涉及到排序的问题，问同事也说没遇到过此类问题，于是自己想了想给出了一个天下最丑的方法（比完全没有好点）。先用UNION构造出一个按自定义ｉｄ序列排序的结果集，将此结果集作为子表LEFT JOIN上要查询的表. 代码如下:

{% codeblock lang:sql %}
SELECT a FROM (
    SELECT 1 AS a
    UNION
    SELECT 5 AS a
    UNION
    SELECT 3 AS a
) AS tb1
LEFT JOIN tbl tb2
ON tb2 .id =  tb1 .a 
WHERE tb2.id IN(1, 5, 3) ;
{% endcodeblock %}

这个方案可行, 但让人看起来就相当恶心, 后来有搜索到可以用FIELD函数来实现此功能, 官方对FIELD的说明为:

    Return the index (position) of the first argument in the subsequent arguments

在SQL Server数据库中, 同样功能的函数名称叫CHARINDEX. 使用FIELD来实现自定义排序功能的SQL如下:

{% codeblock lang:sql %}
SELECT id FROM tbl WHERE id IN (1, 5, 3) ORDER BY FIELD(id, 1, 5, 3)
{%  endcodeblock %}

其实开始用那个UNION的方法也是因为完全不知道有FIELD这个东西, 用那么恶心的方法, 只是就是力量啊~~~

