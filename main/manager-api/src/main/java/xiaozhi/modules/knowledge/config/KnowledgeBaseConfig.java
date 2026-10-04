package xiaozhi.modules.knowledge.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import xiaozhi.modules.knowledge.rag.KnowledgeBaseAdapterFactory;

/**
 * Lớp cấu hình cơ sở kiến thức
 * Định cấu hình các Bean liên quan đến cơ sở kiến thức
 */
@Configuration
public class KnowledgeBaseConfig {

    /**
     * Cung cấp phiên bản Bean của KnowledgeBaseAdapterFactory
     * @return Phiên bản KnowledgeBaseAdapterFactory
     */
    @Bean
    public KnowledgeBaseAdapterFactory knowledgeBaseAdapterFactory() {
        return new KnowledgeBaseAdapterFactory();
    }
}