
import java.util.ArrayList;
import java.util.List;
import java.util.Spliterator;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicLong;
import java.util.concurrent.locks.LockSupport;
import java.util.function.Consumer;
import java.util.function.Supplier;
import java.util.stream.Stream;
import java.util.stream.StreamSupport;

/**
 * Draws elements from one stream and streams Lists of those elements.
 *
 * @param <T>
 * @author Robert Harder
 */
public class StreamBatcher<T> implements Spliterator<List<T>> {

    private final int batchSize;
    private final Spliterator<T> sourceSpliterator;


    public static <T> Stream<List<T>> batch(final int size, final Stream<T> stream) {
        return StreamSupport.stream(new StreamBatcher<>(size, stream), false);
    }

    public static <T> Stream<List<T>> batch(final Stream<T> stream, final int size) {
        return StreamSupport.stream(new StreamBatcher<>(size, stream), false);
    }


    private StreamBatcher(int batchSize, Stream<T> stream) {
        this.batchSize = Math.max(1, batchSize);
        this.sourceSpliterator = stream.spliterator();
    }

    private StreamBatcher(int batchSize, Spliterator<T> sourceSpliterator) {
        this.batchSize = Math.max(1, batchSize);
        this.sourceSpliterator = sourceSpliterator;
    }

    @Override
    public boolean tryAdvance(Consumer<? super List<T>> action) {
        List<T> batch = new ArrayList<>(batchSize);

        //noinspection StatementWithEmptyBody
        while (sourceSpliterator.tryAdvance(batch::add) && batch.size() < batchSize) {
        }

        if (batch.isEmpty()) {
            return false;
        } else {
            action.accept(batch);
            return true;
        }
    }

    @Override
    public Spliterator<List<T>> trySplit() {
        Spliterator<T> s2 = sourceSpliterator.trySplit();
        if (s2 == null) {
            return null;
        } else {
            return new StreamBatcher<>(batchSize, s2);
        }
    }

    @Override
    public long estimateSize() {
        return (sourceSpliterator.estimateSize() / batchSize) + 1;
    }

    @Override
    public int characteristics() {
        return 0;
    }


    public static void main(String[] args) {
        // Simplest example:
        StreamBatcher.batch(3, Stream.of(1, 2, 3, 4, 5, 6, 7, 8, 9, 10)).forEach(System.out::println);

        // This example demonstrates that the underlying stream is consumed "live" not all at once:
        Stream<String> stream = Stream.generate(new Supplier<String>() {
            AtomicLong seq = new AtomicLong(1);

            @Override
            public String get() {
                // Show exactly when get() is called on the underlying stream
                String s = String.format("seq-%d", seq.getAndIncrement());
                System.out.println("Generated: " + s);
                LockSupport.parkNanos("simulated workload", TimeUnit.MILLISECONDS.toNanos((long) (100 * Math.random())));
                return s;
            }
        });
        StreamBatcher.batch(3, stream.limit(10)).forEach(System.out::println);
    }
}