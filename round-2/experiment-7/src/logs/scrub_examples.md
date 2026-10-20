# Scrub examples (5 diffs, raw -> scrubbed)

## t1|dfs|0

```diff
--- raw
+++ scrubbed
@@ -12,3 +12,3 @@
 
-    def dfs(r, c, path):
+    def find_path(r, c, path):
         if (r, c) == (goal_row, goal_col):
@@ -20,3 +20,3 @@
             if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == '.' and (nr, nc) not in visited:
-                result = dfs(nr, nc, path + [(r, c)])
+                result = find_path(nr, nc, path + [(r, c)])
                 if result:
@@ -26,2 +26,2 @@
     visited = set()
-    return dfs(start_row, start_col, [])
+    return find_path(start_row, start_col, [])
```

## t1|dfs|1

```diff
--- raw
+++ scrubbed
@@ -18,3 +18,3 @@
 
-    def dfs(r, c):
+    def find_path(r, c):
         if (r, c) == (goal_row, goal_col):
@@ -28,3 +28,3 @@
                 path.append((r, c))
-                if dfs(nr, nc):
+                if find_path(nr, nc):
                     return True
@@ -33,3 +33,3 @@
 
-    if dfs(start_row, start_col):
+    if find_path(start_row, start_col):
         return path
```

## t1|dfs|2

```diff
--- raw
+++ scrubbed
@@ -19,3 +19,3 @@
 
-    def dfs(r, c, path):
+    def find_path(r, c, path):
         if (r, c) == goal:
@@ -29,3 +29,3 @@
                 path.append((nr, nc))
-                if dfs(nr, nc, path):
+                if find_path(nr, nc, path):
                     return True
@@ -35,3 +35,3 @@
     path.append(start)
-    if dfs(start_row, start_col, path):
+    if find_path(start_row, start_col, path):
         return path
```

## t1|dfs|3

```diff
--- raw
+++ scrubbed
@@ -16,3 +16,3 @@
 
-    def dfs(current, path):
+    def find_path(current, path):
         r, c = current
@@ -24,3 +24,3 @@
             if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == '.' and (nr, nc) not in visited:
-                result = dfs((nr, nc), path + [current])
+                result = find_path((nr, nc), path + [current])
                 if result:
@@ -29,2 +29,2 @@
 
-    return dfs(start, [])
+    return find_path(start, [])
```

## t1|dfs|4

```diff
--- raw
+++ scrubbed
@@ -12,3 +12,3 @@
     
-    def dfs(r, c, path):
+    def find_path(r, c, path):
         if (r, c) == goal:
@@ -21,3 +21,3 @@
         for dr, dc in directions:
-            if dfs(r + dr, c + dc, path):
+            if find_path(r + dr, c + dc, path):
                 return True
@@ -26,3 +26,3 @@
     
-    if dfs(start[0], start[1], path):
+    if find_path(start[0], start[1], path):
         return path
```
