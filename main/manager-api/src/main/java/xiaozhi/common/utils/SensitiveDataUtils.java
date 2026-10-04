package xiaozhi.common.utils;

import java.util.Arrays;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;

import org.apache.commons.lang3.StringUtils;

import cn.hutool.json.JSONObject;

/**
 * Công cụ xử lý dữ liệu nhạy cảm
 */
public class SensitiveDataUtils {

    // Danh sách trường nhạy cảm
    private static final Set<String> SENSITIVE_FIELDS = new HashSet<>(Arrays.asList(
            "api_key", "personal_access_token", "access_token", "token",
            "secret", "access_key_secret", "secret_key"));

    /**
     * Kiểm tra xem một trường có nhạy cảm không
     */
    public static boolean isSensitiveField(String fieldName) {
        return StringUtils.isNotBlank(fieldName) && SENSITIVE_FIELDS.contains(fieldName.toLowerCase());
    }

    /**
     * Ẩn phần giữa của chuỗi
     */
    public static String maskMiddle(String value) {
        if (StringUtils.isBlank(value) || value.length() == 1) {
            return value;
        }

        int length = value.length();
        if (length <= 8) {
            // Chuỗi ngắn giữ lại 2 chuỗi đầu và 2 chuỗi cuối
            return value.substring(0, 2) + "****" + value.substring(length - 2);
        } else {
            // Dây dài giữ lại 4 dây đầu và 4 dây cuối
            int maskLength = length - 8;
            StringBuilder maskBuilder = new StringBuilder();
            for (int i = 0; i < maskLength; i++) {
                maskBuilder.append('*');
            }
            return value.substring(0, 4) + maskBuilder.toString() + value.substring(length - 4);
        }
    }

    /**
     * Xác định xem một chuỗi có phải là giá trị bị che hay không
     */
    public static boolean isMaskedValue(String value) {
        if (StringUtils.isBlank(value)) {
            return false;
        }
        // Giá trị mặt nạ chứa ít nhất 4 ký tự * liên tiếp
        return value.contains("****");
    }

    /**
     * Xử lý các trường nhạy cảm trong JSONObject
     */
    public static JSONObject maskSensitiveFields(JSONObject jsonObject) {
        if (jsonObject == null) {
            return null;
        }

        JSONObject result = new JSONObject();

        for (String key : jsonObject.keySet()) {
            Object value = jsonObject.get(key);

            if (SENSITIVE_FIELDS.contains(key.toLowerCase()) && value instanceof String) {
                result.set(key, maskMiddle((String) value));
            } else if (value instanceof JSONObject) {
                result.set(key, maskSensitiveFields((JSONObject) value));
            } else {
                result.set(key, value);
            }
        }

        return result;
    }

    /**
     * So sánh xem các trường nhạy cảm của hai JSONObject có giống nhau không
     * Đặc biệt tiến hành so sánh riêng biệt cho các trường nhạy cảm như api_key
     */
    public static boolean isSensitiveDataEqual(JSONObject original, JSONObject updated) {
        if (original == null && updated == null) {
            return true;
        }
        if (original == null || updated == null) {
            return false;
        }

        // Trích xuất và so sánh các trường nhạy cảm cụ thể
        return compareSpecificSensitiveFields(original, updated, "api_key") &&
                compareSpecificSensitiveFields(original, updated, "personal_access_token") &&
                compareSpecificSensitiveFields(original, updated, "access_token") &&
                compareSpecificSensitiveFields(original, updated, "token") &&
                compareSpecificSensitiveFields(original, updated, "secret") &&
                compareSpecificSensitiveFields(original, updated, "access_key_secret") &&
                compareSpecificSensitiveFields(original, updated, "secret_key");
    }

    /**
     * So sánh xem các trường nhạy cảm cụ thể trong hai đối tượng JSON có giống nhau không
     * Duyệt qua toàn bộ cây đối tượng JSON, tìm và so sánh các trường nhạy cảm được chỉ định
     */
    private static boolean compareSpecificSensitiveFields(JSONObject original, JSONObject updated, String fieldName) {
        // Trích xuất các trường nhạy cảm được chỉ định từ đối tượng ban đầu
        Map<String, String> originalFields = new HashMap<>();
        extractSpecificSensitiveField(original, originalFields, fieldName, "");

        // Trích xuất các trường nhạy cảm được chỉ định trong đối tượng cập nhật
        Map<String, String> updatedFields = new HashMap<>();
        extractSpecificSensitiveField(updated, updatedFields, fieldName, "");

        // Nếu số lượng trường khác nhau nghĩa là có thêm và bớt.
        if (originalFields.size() != updatedFields.size()) {
            return false;
        }

        // So sánh giá trị của từng trường
        for (Map.Entry<String, String> entry : originalFields.entrySet()) {
            String key = entry.getKey();
            String originalValue = entry.getValue();
            String updatedValue = updatedFields.get(key);

            if (updatedValue == null || !updatedValue.equals(originalValue)) {
                return false;
            }
        }

        return true;
    }

    /**
     * Trích xuất đệ quy các trường nhạy cảm có tên được chỉ định trong đối tượng JSON
     */
    private static void extractSpecificSensitiveField(JSONObject jsonObject, Map<String, String> fieldsMap,
            String targetFieldName, String parentPath) {
        if (jsonObject == null) {
            return;
        }

        for (String key : jsonObject.keySet()) {
            String fullPath = parentPath.isEmpty() ? key : parentPath + "." + key;
            Object value = jsonObject.get(key);

            if (value instanceof JSONObject) {
                // Xử lý đệ quy các đối tượng JSON lồng nhau
                extractSpecificSensitiveField((JSONObject) value, fieldsMap, targetFieldName, fullPath);
            } else if (value instanceof String && key.equalsIgnoreCase(targetFieldName)) {
                // Tìm trường nhạy cảm mục tiêu và lưu đường dẫn cũng như giá trị của nó
                fieldsMap.put(fullPath, (String) value);
            }
        }
    }
}
