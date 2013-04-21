---
layout: post
title: "避免Android开发中EditText自动获取交点弹出键盘"
date: 2013-04-22 00:57
comments: true
categories: Android
---

这个问题应该是默认会把焦点放到EditText上, 设置EditText的android:focusable=false也无济于事.
搜索以后找到一个比较hack的方案, 就是在layout的文件中加入一个空的(宽高为0, 并且强制设置挺它的android:focusable="true"来把默认的焦点"抢"), 这种方式难免让我想到css中的.clearfix, 异曲同工之妙.

根据上述, 例如使用一个LinearLayout(其他的也可以)来把焦点抢掉.  

``` xml
<LinearLayout
            android:id="@+id/dummyView"
            android:layout_width="0dip"
            android:layout_height="0dip"
            android:focusable="true"
            android:focusableInTouchMode="true" />
```

把这个空的LinearLayout放入我们的布局文件, 在打开, EditText就不会再自动获取焦点并弹出键盘了. 我用RelativeLayout测试同样可以, 其他没有亲测, 原理上来说应该是随便使用一个可以获取焦点的元素都可以.

