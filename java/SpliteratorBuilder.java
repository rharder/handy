import java.util.ArrayList;
import java.util.List;
import java.util.Spliterator;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.locks.LockSupport;
import java.util.stream.StreamSupport;

/**
 * A Spliterator that can be built with the add() method and shutdown with close().
 * This works well with StreamSupport.stream(..).
 */
public class SpliteratorBuilder<T> implements Spliterator<T> {
    private static class Element<T> {
        private T value;

        private Element() {
        }

        private Element(T v) {
            value = v;
        }
    }

    private final Element<T> END_OF_QUEUE = new Element<>();
    final BlockingQueue<Element<T>> queue = new LinkedBlockingQueue<>();
    final List<Runnable> closeHooks = new ArrayList<>();

    public void add(T o) {
        queue.offer(new Element<>(o));
    }

    public void close() {
        queue.offer(END_OF_QUEUE);
    }

    public void addOnCloseHook(Runnable r) {
        synchronized (closeHooks) {
            closeHooks.add(r);
        }
    }

    @Override
    public boolean tryAdvance(java.util.function.Consumer<? super T> action) {
        Element<T> e;
        try {
            e = queue.take();
        } catch (InterruptedException interruptedException) {
            interruptedException.printStackTrace();
            e = END_OF_QUEUE;
        }

        if (e == END_OF_QUEUE) {
            synchronized (closeHooks) {
                closeHooks.forEach(Runnable::run);
            }
            return false;
        } else {
            action.accept(e.value);
            return true;
        }

    }

    @Override
    public Spliterator<T> trySplit() {
        return null;
    }

    @Override
    public long estimateSize() {
        return 0;
    }

    @Override
    public int characteristics() {
        return 0;
    }

    /**
     * Example of using the class.
     */
    public static void main(String[] args) {
        final SpliteratorBuilder<String> builder = new SpliteratorBuilder<>();

        // With some random delays, add 10 strings to the stream on another thread
        CompletableFuture.runAsync(() -> {
            for (int i = 0; i < 10; i++) {
                LockSupport.parkNanos((long) (Math.random() * 500000000));
                builder.add("Value is " + i);
            }
            builder.close();
        });

        // On main thread, we're printing that which is getting built asynchronously.
        StreamSupport.stream(builder, false).forEach(System.out::println);
    }

}
