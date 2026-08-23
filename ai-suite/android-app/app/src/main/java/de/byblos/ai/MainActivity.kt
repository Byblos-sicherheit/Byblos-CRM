package de.byblos.ai

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.lifecycle.viewmodel.compose.viewModel
import de.byblos.ai.ui.ChatRoute
import de.byblos.ai.ui.ChatViewModel
import de.byblos.ai.ui.theme.ByblosTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        setContent {
            ByblosTheme {
                val app = application as ByblosApplication
                val chatViewModel: ChatViewModel = viewModel(
                    factory = ChatViewModel.factory(app.container.chatRepository),
                )
                ChatRoute(viewModel = chatViewModel)
            }
        }
    }
}
