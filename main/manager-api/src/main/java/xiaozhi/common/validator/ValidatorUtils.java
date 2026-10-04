package xiaozhi.common.validator;

import java.util.Locale;
import java.util.Set;
import java.util.regex.Pattern;

import org.hibernate.validator.messageinterpolation.ResourceBundleMessageInterpolator;
import org.springframework.context.i18n.LocaleContextHolder;
import org.springframework.context.support.ResourceBundleMessageSource;
import org.springframework.validation.beanvalidation.MessageSourceResourceBundleLocator;

import jakarta.validation.ConstraintViolation;
import jakarta.validation.Validation;
import jakarta.validation.Validator;
import xiaozhi.common.exception.RenException;

/**
 * Lớp công cụ xác minh trình xác thực ngủ đông
 * Tài liệu tham khảo: http://docs.jboss.org/hibernate/validator/6.0/reference/en-US/html_single/
 */
public class ValidatorUtils {

    private static ResourceBundleMessageSource getMessageSource() {
        ResourceBundleMessageSource bundleMessageSource = new ResourceBundleMessageSource();
        bundleMessageSource.setDefaultEncoding("UTF-8");
        bundleMessageSource.setBasenames("i18n/validation");
        return bundleMessageSource;
    }

    /**
     * Đối tượng xác minh
     *
     * @param object Đối tượng cần xác minh
     * @param groups nhóm cần được xác minh
     */
    public static void validateEntity(Object object, Class<?>... groups)
            throws RenException {
        Locale.setDefault(LocaleContextHolder.getLocale());
        Validator validator = Validation.byDefaultProvider().configure().messageInterpolator(
                new ResourceBundleMessageInterpolator(new MessageSourceResourceBundleLocator(getMessageSource())))
                .buildValidatorFactory().getValidator();

        Set<ConstraintViolation<Object>> constraintViolations = validator.validate(object, groups);
        if (!constraintViolations.isEmpty()) {
            ConstraintViolation<Object> constraint = constraintViolations.iterator().next();
            throw new RenException(constraint.getMessage());
        }
    }

    /**
     * Biểu thức chính quy số điện thoại di động quốc tế
     * Mã vùng quốc tế là bắt buộc, định dạng là: +[mã quốc gia][số điện thoại di động]
     * Ví dụ:
     * - +8613800138000
     * - +12345678900
     * - +447123456789
     */
    private static final String INTERNATIONAL_PHONE_REGEX = "^\\+[1-9]\\d{0,3}[1-9]\\d{4,14}$";

    /**
     * Xác minh xem số điện thoại di động có hợp lệ không
     * Mã vùng quốc tế là bắt buộc, định dạng là: +[mã quốc gia][số điện thoại di động]
     * Ví dụ: +8613800138000
     * 
     * @param phone điện thoại di động
     * @return boolean
     */
    public static boolean isValidPhone(String phone) {
        if (phone == null || phone.isEmpty()) {
            return false;
        }

        // Xác minh định dạng số điện thoại di động phải bao gồm mã vùng quốc tế
        Pattern pattern = Pattern.compile(INTERNATIONAL_PHONE_REGEX);
        return pattern.matcher(phone).matches();
    }
}