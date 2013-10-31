---
layout: post
title: "从Java的hashCode方法谈起"
date: 2013-10-31 23:30
comments: true
categories: Java, Android
---



最近在看Effective Java看到hashCode这个方法，之前写代码几乎没有去关注它，即使是把自定义的对象放到HashMap也没去关注细节。今天看到正好深入研究下。首先hashCode这个方法用来干什么的呢？下面是来之Java官方文档的说明：



>Returns a hash code value for the object. This method is supported for the benefit of hash tables such as those provided by HashMap.


>The general contract of hashCode is:

>   * Whenever it is invoked on the same object more than once during an execution of a Java application, the hashCode method must consistently return the same integer, provided no information used in equals comparisons on the object is modified. This integer need not remain consistent from one execution of an application to another execution of the same application.
>   * If two objects are equal according to the equals(Object) method, then calling the hashCode method on each of the two objects must produce the same integer result.
>   * It is not required that if two objects are unequal according to the equals(java.lang.Object) method, then calling the hashCode method on each of the two objects must produce distinct integer results. However, the programmer should be aware that producing distinct integer results for unequal objects may improve the performance of hash tables.

>As much as is reasonably practical, the hashCode method defined by class Object does return distinct integers for distinct objects. (This is typically implemented by converting the internal address of the object into an integer, but this implementation technique is not required by the JavaTM programming language.)

几个关键点， 首先， 实现这个方法是为了他们在hash表中做key时有更好的性能，例如HashMap，其次实现它又三个约束

1. 在应用程序执行区间，同样的对象在equals方法用到的属性没有变化时，多次调用的hashCode的返回值必须一样，同一个应用程序多次执行，每次返回的hashCode不一定要一样。
1. 两个用equals比较相同的对象需要返回相等的hashCode
1. 两个调用equals返回false的对象， 并不要求他们的hashCode返回值不同

另外， hashCode是在Object中实现的（是个native方法），默认的实现是将对象的内部地址转成int返回（多次运行反悔的值不一样是允许的）。


上面文档中说了这个hashCode会在HashMap中使用，那我就来用HashMap做个实验，首先让一个类的hashCode实现返回不同的值。看看把两个对象放到HashMap中以后的存放位置。然后将hashCode改为返回固定的值。再次查看hashMap中对象的存放
``` java
public class Main {
     public static void main(String[] argv) {
          HashMap<HashCodeElement, String> map = new HashMap<HashCodeElement, String>();
          map.put(new HashCodeElement(1), "");
          map.put(new HashCodeElement(2), "”);  // 此处断点
     }

}



public class HashCodeElement {
     public int val;
     public HashCodeElement(int val) {
          this.val = val;
     }
     @Override
     public int hashCode() { // 根据属性值返回不同的hashCode，这个hashCode并不满足上述的三个约束
          return val;  
     }

}

```
debug以后可以看到map变量中数据的分布如下，两个对象散列在了不同的位置：

![1db998dbea7b78ca634c338db9bdd5bb](https://f.cloud.github.com/assets/1309744/1447021/de4d7f06-4240-11e3-9761-a729eb29151c.jpeg)

第二种情况，这个类的所有对象hashCode返回同样的值。
``` java
public class HashCodeElement {
     public int val;
     public HashCodeElement(int val) {
          this.val = val;
     }
     @Override
     public int hashCode() { 
          return 1;          // 全都返回1
     }

}
```
同样调试以后的结果如下图，很显然，因为hashCode相同，在hash的时候出现了冲突，HashMap中使用了拉链法解决冲突，也就出现了下图的结果。

![5b451edbf2927dbd87d4c29e879f892f](https://f.cloud.github.com/assets/1309744/1447025/e6e348ee-4240-11e3-80d6-8c7114a86b94.jpeg)

从上图中可以看出，自己重写hashCode最坏的情况就是所有对象返回同样hashCode，然后使用HashMap（其他hash的集合也一样）变成链表。

之前是用HashMap一直没关注key的hashCode这个方法主要是因为基本上都是用String做key，所以顺便看一下String的hashCode实现。打开源码可以看到String的hashCode方法如下：
``` java
@Override public int hashCode() {
    int hash = hashCode;
    if (hash == 0) {
        if (count == 0) {
            return 0;
        }
        final int end = count + offset;
        final char[] chars = value;
        for (int i = offset; i < end; ++i) {
            hash = 31*hash + chars[i];
        }
        hashCode = hash;
    }
    return hash;
}
```
这里的逻辑很简单，offset默认为0（在有substring时候offset会变化）。这里的hash算法为什么要这样实现改日在研究，不过字符串比较常用的hash算法就是这种，但是为什么31呢？先不纠结与此，继续看一下HashMap中调用hashCode的地方。

下面是HashMap的put方法，
``` java
@Override public V put(K key, V value) {
    if (key == null) {
        return putValueForNullKey(value);
    }

    int hash = secondaryHash(key.hashCode());
    HashMapEntry<K, V>[] tab = table;
    int index = hash & (tab.length - 1);
    for (HashMapEntry<K, V> e = tab[index]; e != null; e = e.next) {
        if (e.hash == hash && key.equals(e.key)) {
            preModify(e);
            V oldValue = e.value;
            e.value = value;
            return oldValue;
        }
    }

    // No entry for (non-null) key is present; create one
    modCount++;
    if (size++ > threshold) {
        tab = doubleCapacity();
        index = hash & (tab.length - 1);
    }
    addNewEntry(key, value, hash, index);
    return null;

}


private static int secondaryHash(int h) {
    // Doug Lea's supplemental hash function
    h ^= (h >>> 20) ^ (h >>> 12);
    return h ^ (h >>> 7) ^ (h >>> 4);

}

```
HashMap中拿到key对象本身的hashCode值以后，又对其做了secondaryHash，至于为什么要做这一次secondaryHash，这里有个讨论http://stackoverflow.com/questions/2538092/why-does-a-hashmap-rehash-the-hashcode-supplied-by-the-key-object。 其实关键在于
``` java
int index = hash & (tab.length - 1);
```
普通开发者写出来的hashCode的返回值key可能太大，不适合直接当做key使用，需要将他们映射到哈希表中，所以需要做上面这行代码的与运算，但是我们的hashCode返回值可能低位不够随机，所以需要secondaryHash一次。


最后，其实eclipse是有自动实现hashCode和equals方法的功能的。

![04e70687d67efb6f83fd1058855c7ef9](https://f.cloud.github.com/assets/1309744/1447026/ec740276-4240-11e3-86f5-67035eb32ed5.jpeg)

![50a033430930ff5d39163ab118e550c1](https://f.cloud.github.com/assets/1309744/1447028/f12d07ae-4240-11e3-8a40-da4a49adb62d.jpeg)


下面是Eclipse生成的hashCode和equals方法
``` java
@Override
public boolean equals(Object obj) {
     if (this == obj)
          return true;
     if (obj == null)
          return false;
     if (getClass() != obj.getClass())
          return false;
     HashCodeElement other = (HashCodeElement) obj;
     if (str == null) {
          if (other.str != null)
               return false;
     } else if (!str.equals(other.str))
          return false;
     if (val != other.val)
          return false;
     return true;
}

@Override
public int hashCode() {
     final int prime = 31;
     int result = 1;
     result = prime * result + ((str == null) ? 0 : str.hashCode());
     result = prime * result + val;
     return result;

}
```
Eclipse生成的这个hashCode方法也是Effective Java中推荐的一种hashCode实现方式。有兴趣的可以写一个包含各种类型属性的类，用eclipse生成一个hashCode方法看看。



