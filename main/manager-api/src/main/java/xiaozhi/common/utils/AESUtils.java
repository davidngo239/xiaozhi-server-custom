package xiaozhi.common.utils;

import java.nio.charset.StandardCharsets;
import java.util.Base64;

import javax.crypto.Cipher;
import javax.crypto.spec.SecretKeySpec;

public class AESUtils {

    private static final String ALGORITHM = "AES";
    private static final String TRANSFORMATION = "AES/ECB/PKCS5Padding";

    /**
     * Mã hóa AES
     * 
     * @param key Khóa (16, 24 hoặc 32 bit)
     * @param plainText Chuỗi được mã hóa
     * @return chuỗi Base64 được mã hóa
     */
    public static String encrypt(String key, String plainText) {
        try {
            // Đảm bảo độ dài khóa là 16, 24 hoặc 32 bit
            byte[] keyBytes = padKey(key.getBytes(StandardCharsets.UTF_8));
            SecretKeySpec secretKey = new SecretKeySpec(keyBytes, ALGORITHM);

            Cipher cipher = Cipher.getInstance(TRANSFORMATION);
            cipher.init(Cipher.ENCRYPT_MODE, secretKey);

            byte[] encryptedBytes = cipher.doFinal(plainText.getBytes(StandardCharsets.UTF_8));
            return Base64.getEncoder().encodeToString(encryptedBytes);
        } catch (Exception e) {
            throw new RuntimeException("AES加密失败", e);
        }
    }

    /**
     * giải mã AES
     * 
     * @param key Khóa (16, 24 hoặc 32 bit)
     * @param encryptedText hóa Chuỗi Base64 sẽ được giải mã
     * @return chuỗi được giải mã
     */
    public static String decrypt(String key, String encryptedText) {
        try {
            // Đảm bảo độ dài khóa là 16, 24 hoặc 32 bit
            byte[] keyBytes = padKey(key.getBytes(StandardCharsets.UTF_8));
            SecretKeySpec secretKey = new SecretKeySpec(keyBytes, ALGORITHM);

            Cipher cipher = Cipher.getInstance(TRANSFORMATION);
            cipher.init(Cipher.DECRYPT_MODE, secretKey);

            byte[] encryptedBytes = Base64.getDecoder().decode(encryptedText);
            byte[] decryptedBytes = cipher.doFinal(encryptedBytes);
            return new String(decryptedBytes, StandardCharsets.UTF_8);
        } catch (Exception e) {
            throw new RuntimeException("AES解密失败", e);
        }
    }

    /**
     * Phím đệm theo độ dài được chỉ định (16, 24 hoặc 32 bit)
     * 
     * @param keyBytes mảng byte khóa gốc
     * @return mảng byte khóa được điền
     */
    private static byte[] padKey(byte[] keyBytes) {
        int keyLength = keyBytes.length;
        if (keyLength == 16 || keyLength == 24 || keyLength == 32) {
            return keyBytes;
        }

        // Nếu độ dài khóa không đủ, hãy điền nó bằng 0; nếu nó vượt quá độ dài khóa, hãy cắt bớt 32 chữ số đầu tiên.
        byte[] paddedKey = new byte[32];
        System.arraycopy(keyBytes, 0, paddedKey, 0, Math.min(keyLength, 32));
        return paddedKey;
    }
}
