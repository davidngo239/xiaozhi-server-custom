package xiaozhi.common.utils;

import org.springframework.context.MessageSource;
import org.springframework.context.i18n.LocaleContextHolder;

/**
 * quốc tế hóa
 * Bản quyền (c) Renren Kaiyuan Mọi quyền được bảo lưu.
 * Website: https://www.renren.io
 */
public class MessageUtils {
    private static MessageSource messageSource;

    public static String getMessage(int code) {
        return getMessage(code, new String[0]);
    }

    public static String getMessage(int code, String... params) {
        if (messageSource == null) {
            // Khởi tạo lười biếng để đảm bảo bối cảnh Spring được khởi tạo đầy đủ
            messageSource = (MessageSource) SpringContextUtils.getBean("messageSource");
        }
        return messageSource.getMessage(code + "", params, LocaleContextHolder.getLocale());
    }
}
