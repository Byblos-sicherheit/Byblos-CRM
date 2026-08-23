package de.byblos.ai.di

import android.content.Context
import androidx.room.Room
import de.byblos.ai.BuildConfig
import de.byblos.ai.data.ChatRepository
import de.byblos.ai.data.DefaultChatRepository
import de.byblos.ai.data.local.AppDatabase
import de.byblos.ai.data.local.Migrations
import de.byblos.ai.data.remote.ChatRemoteDataSource
import de.byblos.ai.data.remote.ClientIdentity
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import java.util.concurrent.TimeUnit

class AppContainer(context: Context) {
    private val clientIdentity = ClientIdentity(context)

    private val database: AppDatabase = Room.databaseBuilder(
        context,
        AppDatabase::class.java,
        AppDatabase.NAME,
    )
        .addMigrations(Migrations.MIGRATION_1_2)
        .build()

    private val httpClient: OkHttpClient = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(0, TimeUnit.MILLISECONDS)
        .writeTimeout(30, TimeUnit.SECONDS)
        .retryOnConnectionFailure(true)
        .apply {
            if (BuildConfig.DEBUG) {
                addInterceptor(
                    HttpLoggingInterceptor().apply {
                        level = HttpLoggingInterceptor.Level.BASIC
                    },
                )
            }
        }
        .build()

    private val remoteDataSource = ChatRemoteDataSource(
        client = httpClient,
        baseUrl = BuildConfig.BACKEND_BASE_URL,
        privateTestingToken = BuildConfig.BACKEND_API_TOKEN,
        clientId = clientIdentity.id,
    )

    val chatRepository: ChatRepository = DefaultChatRepository(
        dao = database.messageDao(),
        remote = remoteDataSource,
    )
}
