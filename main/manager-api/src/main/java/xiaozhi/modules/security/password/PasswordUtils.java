package xiaozhi.modules.security.password;

/**
 * Công cụ mật khẩu
 * Bản quyền (c) Renren Kaiyuan Mọi quyền được bảo lưu.
 * Website: https://www.renren.io
 */
public class PasswordUtils {
    private static PasswordEncoder passwordEncoder = new BCryptPasswordEncoder();

    /**
     * Mã hóa
     *
     * @param str chuỗi
     * @return Trả về chuỗi được mã hóa
     */
    public static String encode(String str) {
        return passwordEncoder.encode(str);
    }

    /**
     * So sánh mật khẩu cho sự bình đẳng
     *
     * @param str mật khẩu văn bản đơn giản
     * @param password khẩu mật khẩu được mã hóa
     * @return true: thành công sai: thất bại
     */
    public static boolean matches(String str, String password) {
        return passwordEncoder.matches(str, password);
    }

    public static void main(String[] args) {
        String str = "admin";
        String password = encode(str);

        System.out.println(password);
        System.out.println(matches(str, password));
    }

}
