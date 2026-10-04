package xiaozhi.modules.security.password;

/**
 * Giao diện dịch vụ mã hóa mật khẩu.
 * <p>
 * Cách triển khai ưu tiên là {@code BCryptPasswordEncoding}.
 *
 * @author Keith Donald
 */
public interface PasswordEncoder {

    /**
     * Mã hóa mật khẩu thô. Nói chung, thuật toán mã hóa tốt sẽ áp dụng SHA-1
     * or
     * hàm băm lớn hơn kết hợp với muối được tạo ngẫu nhiên 8 byte trở lên.
     */
    String encode(CharSequence rawPassword);

    /**
     * Xác minh mật khẩu được mã hóa thu được từ bộ lưu trữ khớp với mật khẩu thô đã gửi
     * mật khẩu sau khi nó cũng được mã hóa. Trả về true nếu mật khẩu khớp, sai
     * if
     * họ không làm vậy. Bản thân mật khẩu được lưu trữ không bao giờ được giải mã.
     *
     * @param rawPassword mật khẩu thô để mã hóa và khớp
     * @param encodedPassword hóaMật khẩu mật khẩu được mã hóa từ bộ lưu trữ để so sánh với
     * @return true nếu mật khẩu thô, sau khi mã hóa, khớp với mã hóa
     *         mật khẩu từ
     *         storage
     */
    boolean matches(CharSequence rawPassword, String encodedPassword);

}
