/*
This file is part of Telegram Desktop,
the official desktop application for the Telegram messaging service.

For license and copyright information please follow this link:
https://github.com/telegramdesktop/tdesktop/blob/master/LEGAL
*/
#pragma once

#include <algorithm>
#include <charconv>
#include <cstdint>
#include <optional>
#include <string_view>

namespace Export {

struct TranscriptionRetryPolicy {
	int pendingAttempts = 0;
	int floodAttempts = 0;

	[[nodiscard]] bool retryPending() {
		floodAttempts = 0;
		return (++pendingAttempts < 36);
	}

	[[nodiscard]] static bool IsFlood(std::string_view error) {
		return error == "FLOOD"
			|| error.starts_with("FLOOD_WAIT_")
			|| error.starts_with("FLOOD_PREMIUM_WAIT_");
	}

	[[nodiscard]] std::optional<std::int64_t> floodDelay(
			std::string_view error) {
		if (!IsFlood(error) || ++floodAttempts > 5) {
			return std::nullopt;
		}
		if (error == "FLOOD") {
			return std::int64_t(30'000) * floodAttempts;
		}
		const auto suffix = error.substr(error.find_last_of('_') + 1);
		auto seconds = std::int32_t(0);
		const auto [end, code] = std::from_chars(
			suffix.data(),
			suffix.data() + suffix.size(),
			seconds);
		if (code != std::errc()
			|| end != suffix.data() + suffix.size()
			|| seconds < 0) {
			return std::nullopt;
		}
		return std::int64_t(std::max(seconds, 1)) * 1000;
	}
};

} // namespace Export
