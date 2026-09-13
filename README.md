# WuwaMatrixReader
Get details about teams you used from a Wuwa's Matrix screenshot. This program gives: Team number, Resonators, Buff Types

[Round Resonator avatars](https://github.com/alt3ri/WW_Asset_Webp/tree/main/UIResources/Common/Image/IconRoleHead175) and [Buff Icons](https://github.com/alt3ri/WW_Asset_Webp/tree/main/UIResources/Common/Image/IconAttribute) are from [WW_Asset_Webp](https://github.com/alt3ri/WW_Asset_Webp)

**How to Use:**

Run ```WuwaMatrixReader.py```

Download images in ```number_images``` to detect Team number

**Input:** 

```PATH to Wuwa Matrix screenshot```~~(not image from Share function)~~

**Output:** 

```a list of dictionary```

Keys of each entry:

```
Team #: an integer, the number of team
Resonators: array of strings, image name of matched resonators
BUFF: a string, image name of matched BUFF icon
Wave Number Area: bounding box of wave number (wave ?)
Monster Count Area: bounding box of monster count (?/5)
Team Score Area: bounding box of team score
```

Bounding box format: ```x0, y0, width, height```



**Python version:** 3.11

*by Dropkick
9/13/2026*
