# OkHttp and Room publish consumer rules. Keep only application models that are
# instantiated reflectively by external tools. This project does not currently
# rely on reflective JSON serialization.

-keepattributes Signature,*Annotation*

# Retain useful source information for de-obfuscating crash reports.
-renamesourcefileattribute SourceFile
-keepattributes SourceFile,LineNumberTable
