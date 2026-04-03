using UnityEngine;
using UnityEngine.UI;
using ProjectD;

namespace ProjectE
{
    /// <summary>
    /// MonoBehaviour entry point for Project E (Unity).
    /// On Start(), runs the full C++ → C# pipeline and displays
    /// the result both in the Unity console and on screen via a UI Text.
    /// </summary>
    public class AppEntry : MonoBehaviour
    {
        private void Start()
        {
            Debug.Log("[ProjectE] Starting pipeline...");
            string message;
            try
            {
                string greeting = Pipeline.Run();
                message = greeting;
                Debug.Log($"[ProjectE] Pipeline result: {greeting}");
            }
            catch (System.Exception ex)
            {
                message = $"Pipeline failed:\n{ex.Message}";
                Debug.LogError($"[ProjectE] Pipeline failed: {ex}");
            }

            CreateScreenText(message);
        }

        private void CreateScreenText(string message)
        {
            // Create Canvas
            var canvasGo = new GameObject("PipelineCanvas");
            var canvas = canvasGo.AddComponent<Canvas>();
            canvas.renderMode = RenderMode.ScreenSpaceOverlay;
            canvasGo.AddComponent<CanvasScaler>();
            canvasGo.AddComponent<GraphicRaycaster>();

            // Create Text
            var textGo = new GameObject("PipelineText");
            textGo.transform.SetParent(canvasGo.transform, false);

            var text = textGo.AddComponent<Text>();
            text.text = message;
            text.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
            text.fontSize = 36;
            text.color = Color.white;
            text.alignment = TextAnchor.MiddleCenter;

            // Fill the screen
            var rect = textGo.GetComponent<RectTransform>();
            rect.anchorMin = Vector2.zero;
            rect.anchorMax = Vector2.one;
            rect.offsetMin = Vector2.zero;
            rect.offsetMax = Vector2.zero;

            // Dark background for readability
            var bgGo = new GameObject("Background");
            bgGo.transform.SetParent(canvasGo.transform, false);
            bgGo.transform.SetAsFirstSibling();
            var bgImage = bgGo.AddComponent<Image>();
            bgImage.color = new Color(0.15f, 0.15f, 0.15f, 1f);
            var bgRect = bgGo.GetComponent<RectTransform>();
            bgRect.anchorMin = Vector2.zero;
            bgRect.anchorMax = Vector2.one;
            bgRect.offsetMin = Vector2.zero;
            bgRect.offsetMax = Vector2.zero;
        }
    }
}
