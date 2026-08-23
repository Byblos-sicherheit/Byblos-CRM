package de.byblos.ai.ui

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertIsEnabled
import androidx.compose.ui.test.assertIsNotEnabled
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.performTextInput
import de.byblos.ai.ui.theme.ByblosTheme
import org.junit.Rule
import org.junit.Test

class ChatScreenTest {
    @get:Rule
    val composeRule = createComposeRule()

    @Test
    fun sendButtonRequiresNonBlankInput() {
        composeRule.setContent {
            ByblosTheme {
                ChatScreen(
                    state = ChatUiState(),
                    onInputChanged = {},
                    onSend = {},
                    onCancel = {},
                    onClear = {},
                    onDismissError = {},
                )
            }
        }

        composeRule.onNodeWithTag("message_input").assertIsDisplayed()
        composeRule.onNodeWithTag("send_button").assertIsNotEnabled()
    }
}
