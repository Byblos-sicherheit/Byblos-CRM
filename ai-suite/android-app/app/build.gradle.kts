plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.compose)
    alias(libs.plugins.ksp)
}

fun String.asBuildConfigString(): String =
    "\"${replace("\\", "\\\\").replace("\"", "\\\"")}\""

val releaseBackendUrl = providers.gradleProperty("BACKEND_BASE_URL")
    .orElse("https://example.invalid/")
val privateTestingToken = providers.gradleProperty("BACKEND_API_TOKEN")
    .orElse("")

android {
    namespace = "de.byblos.ai"
    compileSdk = 37

    defaultConfig {
        applicationId = "de.byblos.ai"
        minSdk = 23
        targetSdk = 37
        versionCode = 1
        versionName = "1.0.0"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        vectorDrawables.useSupportLibrary = true
    }

    buildTypes {
        debug {
            applicationIdSuffix = ".debug"
            versionNameSuffix = "-debug"
            manifestPlaceholders["usesCleartextTraffic"] = "true"
            buildConfigField(
                "String",
                "BACKEND_BASE_URL",
                "http://10.0.2.2:3000/".asBuildConfigString(),
            )
            buildConfigField(
                "String",
                "BACKEND_API_TOKEN",
                privateTestingToken.get().asBuildConfigString(),
            )
        }

        release {
            isMinifyEnabled = true
            isShrinkResources = true
            manifestPlaceholders["usesCleartextTraffic"] = "false"
            buildConfigField(
                "String",
                "BACKEND_BASE_URL",
                releaseBackendUrl.get().asBuildConfigString(),
            )
            buildConfigField(
                "String",
                "BACKEND_API_TOKEN",
                privateTestingToken.get().asBuildConfigString(),
            )
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro",
            )
        }
    }

    buildFeatures {
        compose = true
        buildConfig = true
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    packaging {
        resources.excludes += setOf(
            "/META-INF/{AL2.0,LGPL2.1}",
            "META-INF/LICENSE.md",
            "META-INF/LICENSE-notice.md",
        )
    }

    testOptions {
        unitTests.isIncludeAndroidResources = true
    }
}


ksp {
    arg("room.schemaLocation", "$projectDir/schemas")
    arg("room.incremental", "true")
}


val validateReleaseConfiguration by tasks.registering {
    group = "verification"
    description = "Rejects unsafe or placeholder release backend configuration."

    doLast {
        val rawUrl = releaseBackendUrl.get().trim()
        val uri = runCatching { java.net.URI(rawUrl) }
            .getOrElse { throw GradleException("BACKEND_BASE_URL must be a valid absolute URL") }

        if (uri.scheme != "https") {
            throw GradleException("BACKEND_BASE_URL must use HTTPS for release builds")
        }
        if (uri.host.isNullOrBlank() || uri.host.endsWith(".invalid")) {
            throw GradleException("BACKEND_BASE_URL must point to a real production host")
        }
    }
}

tasks.matching { it.name == "preReleaseBuild" }.configureEach {
    dependsOn(validateReleaseConfiguration)
}

dependencies {
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.activity.compose)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    implementation(libs.androidx.lifecycle.runtime.compose)
    implementation(libs.androidx.lifecycle.viewmodel.compose)
    implementation(libs.androidx.lifecycle.viewmodel.ktx)
    implementation(libs.kotlinx.coroutines.android)

    val composeBom = platform(libs.androidx.compose.bom)
    implementation(composeBom)
    androidTestImplementation(composeBom)
    implementation(libs.androidx.compose.ui)
    implementation(libs.androidx.compose.ui.tooling.preview)
    implementation(libs.androidx.compose.material3)
    implementation(libs.androidx.compose.icons)
    debugImplementation(libs.androidx.compose.ui.tooling)

    implementation(libs.androidx.room.runtime)
    implementation(libs.androidx.room.ktx)
    ksp(libs.androidx.room.compiler)

    implementation(platform(libs.okhttp.bom))
    implementation(libs.okhttp.core)
    implementation(libs.okhttp.logging)
    implementation(libs.okhttp.sse)


    testImplementation(libs.junit)
    testImplementation(libs.kotlinx.coroutines.test)

    androidTestImplementation(libs.androidx.test.core)
    androidTestImplementation(libs.androidx.test.runner)
    androidTestImplementation(libs.androidx.test.ext.junit)
    androidTestImplementation(libs.androidx.test.espresso.core)
    androidTestImplementation(libs.androidx.sqlite.framework)
    androidTestImplementation(libs.androidx.compose.ui.test.junit4)
    debugImplementation(libs.androidx.compose.ui.test.manifest)
}
