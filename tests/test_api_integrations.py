import os
import unittest
from unittest.mock import patch, MagicMock
import requests

from services.gemini_service import (
    call_groq_api,
    chat_with_gemini,
    generate_itinerary_ai,
    MODELS_TO_TRY,
    GROQ_API_URL,
)
from services.weather_service import get_weather_for_city, get_mock_weather
from services.translate_service import translate_text
from services.maps_service import get_map_embed_url, get_directions_url
from app import app


class TestGroqAIIntegration(unittest.TestCase):
    """Tests for Groq AI chat and itinerary integrations."""

    def test_active_production_models_configured(self):
        """Verify only supported active models are configured (no gemma2-9b-it or mixtral)."""
        self.assertIn("llama-3.1-8b-instant", MODELS_TO_TRY)
        self.assertIn("llama-3.3-70b-versatile", MODELS_TO_TRY)
        self.assertNotIn("gemma2-9b-it", MODELS_TO_TRY)
        self.assertNotIn("mixtral-8x7b-32768", MODELS_TO_TRY)

    @patch("services.gemini_service.requests.post")
    def test_call_groq_api_success_200(self, mock_post):
        """Test successful response parsing from Groq API."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Welcome to Marina Beach!"}}]
        }
        mock_post.return_value = mock_response

        reply = call_groq_api("valid_key_123", "llama-3.1-8b-instant", "Tell me about Marina Beach")
        self.assertEqual(reply, "Welcome to Marina Beach!")
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs["json"]["model"], "llama-3.1-8b-instant")
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer valid_key_123")

    def test_call_groq_api_missing_or_placeholder_key(self):
        """Missing or placeholder key raises ValueError immediately without calling network."""
        with self.assertRaises(ValueError):
            call_groq_api("", "llama-3.1-8b-instant", "hi")
        with self.assertRaises(ValueError):
            call_groq_api("your_groq_api_key_here", "llama-3.1-8b-instant", "hi")

    @patch("services.gemini_service.requests.post")
    def test_call_groq_api_auth_error_401_no_retry(self, mock_post):
        """HTTP 401 is non-retryable and fails immediately without repeated attempts."""
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_post.return_value = mock_resp

        with self.assertRaises(Exception) as ctx:
            call_groq_api("bad_key", "llama-3.1-8b-instant", "hello", retries=3)

        self.assertIn("Authentication/authorization error (HTTP 401)", str(ctx.exception))
        # Verify it was only called once, NOT retried 3 times
        self.assertEqual(mock_post.call_count, 1)

    @patch("services.gemini_service.requests.post")
    def test_call_groq_api_auth_error_403_no_retry(self, mock_post):
        """HTTP 403 Forbidden is non-retryable and fails immediately."""
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_post.return_value = mock_resp

        with self.assertRaises(Exception) as ctx:
            call_groq_api("blocked_key", "llama-3.1-8b-instant", "hello", retries=3)

        self.assertIn("Authentication/authorization error (HTTP 403)", str(ctx.exception))
        self.assertEqual(mock_post.call_count, 1)

    @patch("services.gemini_service.requests.post")
    def test_call_groq_api_model_error_400_or_404(self, mock_post):
        """HTTP 400 or 404 for deprecated model returns descriptive error without retry loop."""
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.json.return_value = {"error": {"message": "The model `retired_model` does not exist"}}
        mock_post.return_value = mock_resp

        with self.assertRaises(Exception) as ctx:
            call_groq_api("valid_key", "retired_model", "hello", retries=3)

        self.assertIn("Model retired_model error", str(ctx.exception))
        self.assertEqual(mock_post.call_count, 1)

    @patch("services.gemini_service.time.sleep")
    @patch("services.gemini_service.requests.post")
    def test_call_groq_api_rate_limit_429_then_success(self, mock_post, mock_sleep):
        """HTTP 429 triggers exponential backoff and succeeds on next attempt."""
        resp_429 = MagicMock()
        resp_429.status_code = 429

        resp_200 = MagicMock()
        resp_200.status_code = 200
        resp_200.json.return_value = {"choices": [{"message": {"content": "Success after 429"}}]}

        mock_post.side_effect = [resp_429, resp_200]

        reply = call_groq_api("valid_key", "llama-3.1-8b-instant", "hi", retries=3)
        self.assertEqual(reply, "Success after 429")
        self.assertEqual(mock_post.call_count, 2)
        mock_sleep.assert_called_with(1)  # 2**0 = 1 second

    @patch("services.gemini_service.time.sleep")
    @patch("services.gemini_service.requests.post")
    def test_call_groq_api_500_server_error_retry(self, mock_post, mock_sleep):
        """HTTP 500 retries and then raises descriptive error."""
        resp_500 = MagicMock()
        resp_500.status_code = 500

        mock_post.return_value = resp_500

        with self.assertRaises(Exception) as ctx:
            call_groq_api("valid_key", "llama-3.1-8b-instant", "hi", retries=2)

        self.assertIn("500", str(ctx.exception))
        self.assertEqual(mock_post.call_count, 2)

    @patch("services.gemini_service.time.sleep")
    @patch("services.gemini_service.requests.post")
    def test_call_groq_api_timeout_retry(self, mock_post, mock_sleep):
        """Connection timeout is caught and retried."""
        mock_post.side_effect = requests.exceptions.Timeout("Read timeout")

        with self.assertRaises(Exception) as ctx:
            call_groq_api("valid_key", "llama-3.1-8b-instant", "hi", retries=2)

        self.assertIn("timed out", str(ctx.exception))
        self.assertEqual(mock_post.call_count, 2)

    @patch.dict(os.environ, {"GROQ_API_KEY": "your_groq_api_key_here"})
    def test_chat_with_gemini_missing_key_fallback(self):
        """Placeholder key returns friendly setup message without throwing exceptions."""
        response = chat_with_gemini("Tell me about Chennai")
        self.assertIn("Setup Required", response)
        self.assertIn("GROQ_API_KEY", response)

    @patch.dict(os.environ, {"GROQ_API_KEY": "valid_key"})
    @patch("services.gemini_service.call_groq_api")
    def test_generate_itinerary_ai_success(self, mock_call):
        """Successful itinerary generation returns markdown."""
        mock_call.return_value = "### 1-Day Chennai Plan\n- Marina Beach\n- Kapaleeshwarar Temple"
        itinerary = generate_itinerary_ai("Chennai", 1)
        self.assertIn("Marina Beach", itinerary)
        mock_call.assert_called_once()

    @patch.dict(os.environ, {"GROQ_API_KEY": "valid_key"})
    @patch("services.gemini_service.call_groq_api")
    def test_generate_itinerary_ai_model_failure_fallback(self, mock_call):
        """If AI call fails, gracefully returns high-quality curated itinerary."""
        mock_call.side_effect = Exception("API rate limited")
        itinerary = generate_itinerary_ai("Chennai", 1)
        self.assertIn("Marina Beach", itinerary)
        self.assertIn("Total Estimated Daily Cost", itinerary)


class TestWeatherIntegration(unittest.TestCase):
    """Tests for OpenWeatherMap integration."""

    @patch.dict(os.environ, {"OPENWEATHERMAP_API_KEY": ""})
    def test_weather_missing_key_returns_mock(self):
        """When API key is not configured, returns realistic seasonal demo data with note."""
        result = get_weather_for_city("chennai")
        self.assertTrue(result["is_mock"])
        self.assertIn("temperature", result)
        self.assertIn("Demo seasonal weather", result.get("note", ""))

    @patch.dict(os.environ, {"OPENWEATHERMAP_API_KEY": "your_openweathermap_api_key_here"})
    def test_weather_placeholder_key_does_not_call_api(self):
        """Placeholder key does not make network calls and returns demo data."""
        with patch("services.weather_service.requests.get") as mock_get:
            result = get_weather_for_city("coimbatore")
            mock_get.assert_not_called()
            self.assertTrue(result["is_mock"])

    @patch.dict(os.environ, {"OPENWEATHERMAP_API_KEY": "valid_weather_key"})
    @patch("services.weather_service.requests.get")
    def test_weather_live_200_success(self, mock_get):
        """Live weather API response is parsed into clean structure."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "main": {"temp": 29.5, "humidity": 65},
            "weather": [{"main": "Clear", "description": "clear sky", "icon": "01d"}]
        }
        mock_get.return_value = mock_resp

        result = get_weather_for_city("chennai")
        self.assertFalse(result["is_mock"])
        self.assertEqual(result["temperature"], "29.5°C")
        self.assertEqual(result["humidity"], "65%")
        self.assertEqual(result["condition"], "Clear")
        self.assertEqual(result["icon"], "01d")

    @patch.dict(os.environ, {"OPENWEATHERMAP_API_KEY": "valid_weather_key"})
    @patch("services.weather_service.requests.get")
    def test_weather_api_failure_fallback(self, mock_get):
        """Live weather API failure gracefully falls back to seasonal data with failure note."""
        mock_get.side_effect = requests.exceptions.HTTPError("401 Unauthorized")

        result = get_weather_for_city("kanyakumari")
        self.assertTrue(result["is_mock"])
        self.assertIn("Live weather API unavailable", result.get("note", ""))

    def test_weather_invalid_city(self):
        """Non-allowlisted coordinates return error object."""
        result = get_weather_for_city("unknown_city_xyz")
        self.assertIn("error", result)


class TestTranslationIntegration(unittest.TestCase):
    """Tests for LibreTranslate integration."""

    def test_translate_english_noop(self):
        """English target language returns text directly without calling translation API."""
        with patch("services.translate_service.requests.post") as mock_post:
            output = translate_text("Hello World", "en")
            self.assertEqual(output, "Hello World")
            mock_post.assert_not_called()

    @patch("services.translate_service.requests.post")
    def test_translate_success_200(self, mock_post):
        """Successful translation returns translated text."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"translatedText": "வணக்கம்"}
        mock_post.return_value = mock_resp

        output = translate_text("Hello", "ta")
        self.assertEqual(output, "வணக்கம்")

    @patch("services.translate_service.requests.post")
    def test_translate_trailing_slash_handled(self, mock_post):
        """LIBRETRANSLATE_URL with trailing slash produces clean URL without double-slash."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"translatedText": "வணக்கம்"}
        mock_post.return_value = mock_resp

        with patch.dict(os.environ, {"LIBRETRANSLATE_URL": "https://translate.example.com/"}):
            translate_text("Hello", "ta")
            args, _ = mock_post.call_args
            self.assertEqual(args[0], "https://translate.example.com/translate")

    @patch("services.translate_service.requests.post")
    def test_translate_api_failure_graceful_fallback(self, mock_post):
        """Failed translation retains original English text with an informative disclaimer."""
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_post.return_value = mock_resp

        output = translate_text("Original English text", "ta")
        self.assertIn("Original English text", output)
        self.assertIn("temporarily unavailable", output)


class TestGoogleMapsIntegration(unittest.TestCase):
    """Tests for Google Maps embed and directions integrations."""

    @patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": ""})
    def test_maps_embed_no_key_standard_free_iframe(self):
        """When no key is configured, uses free coordinates embed."""
        url = get_map_embed_url(13.0827, 80.2707, "Marina Beach")
        self.assertTrue(url.startswith("https://maps.google.com/maps?q=13.0827,80.2707"))
        self.assertIn("output=embed", url)
        self.assertNotIn("key=", url)

    @patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "your_google_maps_api_key_here"})
    def test_maps_embed_placeholder_key_falls_back_to_free(self):
        """Placeholder key does NOT break the iframe; cleanly uses free embed."""
        url = get_map_embed_url(13.0827, 80.2707, "Marina Beach")
        self.assertTrue(url.startswith("https://maps.google.com/maps?q=13.0827,80.2707"))
        self.assertNotIn("key=", url)

    @patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "AIzaSyRealApiKey123"})
    def test_maps_embed_with_valid_key(self):
        """Valid key uses official Maps Embed API."""
        url = get_map_embed_url(13.0827, 80.2707, "Marina Beach")
        self.assertTrue(url.startswith("https://www.google.com/maps/embed/v1/place"))
        self.assertIn("key=AIzaSyRealApiKey123", url)
        self.assertIn("Marina%20Beach", url)

    def test_directions_url(self):
        """Directions URL uses standard free Google Maps navigation."""
        url = get_directions_url(13.0827, 80.2707)
        self.assertEqual(url, "https://www.google.com/maps/dir/?api=1&destination=13.0827,80.2707")


class TestFlaskRoutesAndSecurity(unittest.TestCase):
    """Integration tests for Flask routes verifying security and API contracts."""

    def setUp(self):
        self.client = app.test_client()

    def test_root_route_and_security_headers(self):
        """Root route returns 200 with all required security headers."""
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(res.headers.get("X-Frame-Options"), "DENY")
        self.assertIn("default-src 'self'", res.headers.get("Content-Security-Policy", ""))

    def test_weather_endpoint_valid_city(self):
        """Endpoint /weather/chennai returns valid JSON."""
        res = self.client.get("/weather/chennai")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("temperature", data)
        self.assertEqual(data["city"], "Chennai")

    def test_weather_endpoint_invalid_city(self):
        """Invalid city returns 400 Bad Request."""
        res = self.client.get("/weather/paris")
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertIn("error", data)

    def test_itinerary_endpoint_contract(self):
        """Endpoint /itinerary/chennai/2 returns itinerary JSON without leaking keys."""
        res = self.client.get("/itinerary/chennai/2")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["city"], "Chennai")
        self.assertEqual(data["days"], 2)
        self.assertIn("itinerary", data)
        # Ensure no secrets in output
        self.assertNotIn("AIzaSy", str(data))
        self.assertNotIn("gsk_", str(data))

    def test_chat_endpoint_requires_json(self):
        """Form submission without application/json Content-Type is rejected with 415."""
        res = self.client.post("/chat", data="message=hello")
        self.assertEqual(res.status_code, 415)

    def test_chat_endpoint_empty_message_400(self):
        """Empty message content is rejected with 400."""
        res = self.client.post("/chat", json={"message": ""})
        self.assertEqual(res.status_code, 400)


if __name__ == "__main__":
    unittest.main()
