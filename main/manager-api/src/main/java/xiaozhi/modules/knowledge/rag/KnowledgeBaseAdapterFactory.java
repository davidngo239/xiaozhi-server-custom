package xiaozhi.modules.knowledge.rag;

import java.util.HashMap;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

import lombok.extern.slf4j.Slf4j;
import xiaozhi.common.exception.ErrorCode;
import xiaozhi.common.exception.RenException;

/**
 * Lớp Nhà máy Bộ điều hợp Cơ sở Kiến thức
 * Chịu trách nhiệm tạo và quản lý các loại bộ điều hợp API cơ sở kiến thức khác nhau
 */
@Slf4j
public class KnowledgeBaseAdapterFactory {

    // Ánh xạ loại bộ điều hợp đã đăng ký
    private static final Map<String, Class<? extends KnowledgeBaseAdapter>> adapterRegistry = new HashMap<>();

    // Bộ nhớ đệm phiên bản bộ điều hợp
    private static final Map<String, KnowledgeBaseAdapter> adapterCache = new ConcurrentHashMap<>();

    // Số lượng phiên bản bộ nhớ đệm tối đa để tránh rò rỉ bộ nhớ (Vấn đề 9)
    private static final int MAX_CACHE_SIZE = 50;

    static {
        // Đăng ký loại bộ điều hợp tích hợp
        registerAdapter("ragflow", xiaozhi.modules.knowledge.rag.impl.RAGFlowAdapter.class);
        // Nhiều loại bộ chuyển đổi có thể được đăng ký tại đây
    }

    /**
     * Đăng ký loại bộ điều hợp mới
     * 
     * @param adapterType Mã định danh loại bộ điều hợp
     * @param adapterClass Lớp bộ điều hợp
     */
    public static void registerAdapter(String adapterType, Class<? extends KnowledgeBaseAdapter> adapterClass) {
        if (adapterRegistry.containsKey(adapterType)) {
            log.warn("适配器类型 '{}' 已存在，将被覆盖", adapterType);
        }
        adapterRegistry.put(adapterType, adapterClass);
        log.info("注册适配器类型: {} -> {}", adapterType, adapterClass.getSimpleName());
    }

    /**
     * Nhận phiên bản bộ chuyển đổi
     * 
     * @param adapterType loại bộ điều hợp
     * @param config Thông số cấu hình
     * @return phiên bản bộ chuyển đổi
     */
    public static KnowledgeBaseAdapter getAdapter(String adapterType, Map<String, Object> config) {
        String cacheKey = buildCacheKey(adapterType, config);

        // Kiểm tra xem phiên bản đã tồn tại trong bộ đệm chưa
        if (adapterCache.containsKey(cacheKey)) {
            log.debug("从缓存获取适配器实例: {}", cacheKey);
            return adapterCache.get(cacheKey);
        }

        // Tạo một phiên bản bộ điều hợp mới
        KnowledgeBaseAdapter adapter = createAdapter(adapterType, config);

        // Phiên bản bộ điều hợp bộ đệm (có kiểm tra giới hạn dung lượng)
        if (adapterCache.size() >= MAX_CACHE_SIZE) {
            log.warn("适配器缓存已达上限 ({})，执行内存保护性清除", MAX_CACHE_SIZE);
            // Xử lý đơn giản: xóa trực tiếp, nên sử dụng LRU trong môi trường sản xuất
            adapterCache.clear();
        }

        adapterCache.put(cacheKey, adapter);
        log.info("创建并缓存适配器实例: {}", cacheKey);

        return adapter;
    }

    /**
     * Nhận phiên bản bộ điều hợp (không có cấu hình)
     * 
     * @param adapterType loại bộ điều hợp
     * @return phiên bản bộ chuyển đổi
     */
    public static KnowledgeBaseAdapter getAdapter(String adapterType) {
        return getAdapter(adapterType, null);
    }

    /**
     * Nhận tất cả các loại bộ điều hợp đã đăng ký
     * 
     * Bộ sưu tập loại bộ điều hợp @return
     */
    public static Set<String> getRegisteredAdapterTypes() {
        return adapterRegistry.keySet();
    }

    /**
     * Kiểm tra xem loại bộ chuyển đổi đã được đăng ký chưa
     * 
     * @param adapterType loại bộ điều hợp
     * @return xem nó đã được đăng ký chưa
     */
    public static boolean isAdapterTypeRegistered(String adapterType) {
        return adapterRegistry.containsKey(adapterType);
    }

    /**
     * Xóa bộ nhớ đệm của bộ điều hợp
     */
    public static void clearCache() {
        int cacheSize = adapterCache.size();
        adapterCache.clear();
        log.info("清除适配器缓存，共清除 {} 个实例", cacheSize);
    }

    /**
     * Xóa bộ đệm cho một loại bộ điều hợp cụ thể
     * 
     * @param adapterType loại bộ điều hợp
     */
    public static void removeCacheByType(String adapterType) {
        int removedCount = 0;
        for (String cacheKey : adapterCache.keySet()) {
            if (cacheKey.startsWith(adapterType + "@")) {
                adapterCache.remove(cacheKey);
                removedCount++;
            }
        }
        log.info("移除适配器类型 '{}' 的缓存，共移除 {} 个实例", adapterType, removedCount);
    }

    /**
     * Nhận thông tin trạng thái nhà máy bộ chuyển đổi
     * 
     * @return thông tin trạng thái
     */
    public static Map<String, Object> getFactoryStatus() {
        Map<String, Object> status = new HashMap<>();
        status.put("registeredAdapterTypes", adapterRegistry.keySet());
        status.put("cachedAdapterCount", adapterCache.size());
        status.put("cacheKeys", adapterCache.keySet());
        return status;
    }

    /**
     * Tạo phiên bản bộ chuyển đổi
     * 
     * @param adapterType loại bộ điều hợp
     * @param config Thông số cấu hình
     * @return phiên bản bộ chuyển đổi
     */
    private static KnowledgeBaseAdapter createAdapter(String adapterType, Map<String, Object> config) {
        if (!adapterRegistry.containsKey(adapterType)) {
            throw new RenException(ErrorCode.RAG_ADAPTER_TYPE_NOT_SUPPORTED,
                    "不支持的适配器类型: " + adapterType);
        }

        try {
            Class<? extends KnowledgeBaseAdapter> adapterClass = adapterRegistry.get(adapterType);
            KnowledgeBaseAdapter adapter = adapterClass.getDeclaredConstructor().newInstance();

            // Khởi tạo bộ chuyển đổi
            if (config != null) {
                adapter.initialize(config);

                // Xác minh cấu hình
                if (!adapter.validateConfig(config)) {
                    throw new RenException(ErrorCode.RAG_CONFIG_VALIDATION_FAILED,
                            "适配器配置验证失败: " + adapterType);
                }
            }

            log.info("成功创建适配器实例: {}", adapterType);
            return adapter;

        } catch (Exception e) {
            log.error("创建适配器实例失败: {}", adapterType, e);
            throw new RenException(ErrorCode.RAG_ADAPTER_CREATION_FAILED,
                    "创建适配器失败: " + adapterType + ", 错误: " + e.getMessage());
        }
    }

    /**
     * Xây dựng khóa bộ đệm
     * 
     * @param adapterType loại bộ điều hợp
     * @param config Thông số cấu hình
     * @return khóa bộ đệm
     */
    private static String buildCacheKey(String adapterType, Map<String, Object> config) {
        if (config == null || config.isEmpty()) {
            return adapterType + "@default";
        }

        // Tạo khóa bộ đệm dựa trên các tham số cấu hình
        StringBuilder keyBuilder = new StringBuilder(adapterType + "@");

        // Sử dụng hàm băm được định cấu hình như một phần của khóa bộ đệm
        int configHash = config.hashCode();
        keyBuilder.append(configHash);

        return keyBuilder.toString();
    }
}