package de.byblos.ai.data.remote

import android.content.Context
import java.util.UUID

class ClientIdentity(context: Context) {
    private val preferences = context.applicationContext.getSharedPreferences(
        PREFERENCES_NAME,
        Context.MODE_PRIVATE,
    )

    val id: String by lazy(LazyThreadSafetyMode.SYNCHRONIZED) {
        preferences.getString(KEY_CLIENT_ID, null)
            ?.takeIf(::isValidIdentifier)
            ?: UUID.randomUUID().toString().also { generated ->
                preferences.edit().putString(KEY_CLIENT_ID, generated).apply()
            }
    }

    private fun isValidIdentifier(value: String): Boolean =
        value.length in 8..128 && value.all { character ->
            character.isLetterOrDigit() || character in "._:-"
        }

    private companion object {
        const val PREFERENCES_NAME = "byblos_client_identity"
        const val KEY_CLIENT_ID = "client_id"
    }
}
