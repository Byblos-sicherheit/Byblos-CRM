package de.byblos.ai

import android.app.Application
import de.byblos.ai.di.AppContainer

class ByblosApplication : Application() {
    val container: AppContainer by lazy {
        AppContainer(applicationContext)
    }
}
