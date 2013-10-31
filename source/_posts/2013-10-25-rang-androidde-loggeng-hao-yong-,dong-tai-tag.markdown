---
layout: post
title: "让Android的Log更好用(动态TAG)"
date: 2013-10-25 19:47
comments: true
categories: 
---


Android开发中， 如果要问用得最多的是哪个类， 肯定大部分人都会说Log，但是其实Log是个很烦人的东西，每次都是 Log.d(“xxxTag”， “内容”);
这样的格式在写，但是项目小的时候这样写不同的Log还能忍受，这就够用了，但是项目文件越来越多，为了区分是哪里打印的Log，通常情况我们会需要写 Log.d(className + methodName +“xxxTag”， “内容”);  这样写多了，肯定会想，有没有办法动态Tag，自动添加类名和方法名字呢？下面我通过callstack来动态的生成了Tag，实现代码如下：

``` java
public class Logger {
     private static final int STACK_TRACE_DEEP = 4;

     private static String DEFAULT_TAG = "EricHua";

     public static String getTag(String subTag, int index) {
          StackTraceElement[] traces = Thread.currentThread().getStackTrace();  // 最核心的方法
          if (index < 0 || index >= traces.length) {
               return "";
          }
          String clsName = traces[index].getClassName();
          String methodName = traces[index].getMethodName();
          String shortClsName = "";
          int dot = clsName.lastIndexOf('.');
          if (dot != -1) {
               shortClsName = clsName.substring(dot + 1);
          }

          if (CommonUtil.ckIsEmpty(subTag)) {
               return DEFAULT_TAG + " " + shortClsName + "." + methodName;
          } else {
               return DEFAULT_TAG + ">" + subTag + " " + shortClsName + "."
               + methodName;
          }

     }     

     public static int d(String msg) {
          return Log.d(getTag(null, STACK_TRACE_DEEP), msg);

     }

}
```


其中最关键的Thread.currentThread().getStackTrace()， 它获取了当前线程的调用栈，当时其中STACK_TRACE_DEEP是什么东西呢？ 这是调用Log.d方法的在栈中的位置，为了确定此值，只需要在getTag方法第一行打上断点，我们在某项目的MainActivity 的onCreate方法中调用Logger.d方法。然后调试，运行以后可以看到调用栈和traces的值分别如下： 

![thread_stack](https://f.cloud.github.com/assets/1309744/1407407/82251622-3d6c-11e3-9da0-6f53469a2dba.jpeg)

调用栈中处于第四层，再看，但是其实这并不是MainActivity在StackTrace中的位置，我们在直接看一下traces的值，展开以后如下：

![debug_info](https://f.cloud.github.com/assets/1309744/1407411/8cffe216-3d6c-11e3-9e9a-e8d69f13e312.jpeg)

这里应该所有调用都是这个层次关系， 所以到此也就可以确定了上面代码中的STACK_TRACE_DEEP的值应该为4。在上面的debug信息中，我们可以看到StackTraceElement对象的一些基本属性。我在上面的代码示例中只用到了className和methodName，实际上如果想要调试更加方便，可以把declaringClass和lineNumber也打印出来更方便定位问题。


至此Tag已经可以动态了，但是如果加上代码混淆，这些tag肯定也是混淆过的名字，可能仍然不利于定位，但是目前能想到的处理方法就是用混淆过的类名和方法名去混淆对应表中找。目前我自己没有特别好的方法可以解决这个问题。